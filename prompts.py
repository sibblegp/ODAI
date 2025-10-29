"""Prompt generation and request analysis module.

This module handles generating suggested prompts based on conversation history
and available agent capabilities. It also determines whether user requests have
been successfully handled and tracks unhandled requests for product improvement.
"""

import json
from typing import Any, Dict, List

from agents import Agent, Handoff, Tool, TResponseInputItem, FunctionTool
from openai import OpenAI
from typing import get_args

try:
    from connectors.utils.segment import track_unhandled_request
except ImportError:
    from .connectors.utils.segment import track_unhandled_request
try:
    from config import Settings
except ImportError as e:
    print(e)
    from .config import Settings
try:
    from firebase import User
except ImportError:
    from .firebase import User

# Initialize settings and OpenAI client
SETTINGS = Settings()
OPENAI_CLIENT = OpenAI(api_key=SETTINGS.openai_api_key)

# Import orchestrator agent to get available agents and tools
try:
    from connectors.orchestrator import ORCHESTRATOR_AGENT, TOOL_CALLS
except ImportError:
    from .connectors.orchestrator import ORCHESTRATOR_AGENT, TOOL_CALLS


class AgentCapabilities:
    """Analyzes and manages available agent capabilities and tools.

    This class parses through the orchestrator agent's handoffs and tools
    to build a comprehensive understanding of system capabilities for
    prompt generation and request analysis.
    """

    def __init__(self):
        # print('Parsing agent capabilities')
        self.parse_agent_capabilities()

    def parse_agent_capabilities(self):
        """
        Parse through all handoffs in ORCHESTRATOR_AGENT and extract their tool definitions and available handoffs.

        Returns:
            Dict containing agent capabilities with tools and handoffs for each agent
        """
        agent_capabilities = {}

        for agent in ORCHESTRATOR_AGENT.handoffs:
            if isinstance(agent, Agent):
                agent_name = agent.name
            else:
                agent_name = str(agent)
            agent_info = {
                "name": agent_name,
                "model": getattr(agent, 'model', 'Unknown'),
                "description": getattr(agent, 'handoff_description', getattr(agent, 'instructions', 'No description available')),
                "tools": [],
                "handoffs": []
            }

            # Extract tools
            if isinstance(agent, Agent):
                if hasattr(agent, 'tools') and agent.tools:
                    for tool in agent.tools:
                        # Check if tool is an instance of any Tool type (Tool is a Union)
                        tool_types = get_args(Tool)
                        if any(isinstance(tool, t) for t in tool_types):
                            tool_info = {
                                "name": tool.name if hasattr(tool, 'name') else str(tool),
                                "description": getattr(tool, 'description', 'No description available'),
                                "parameters": {}
                            }

                            # Try to extract function signature if available
                            # Fix: Avoid accessing tool.function for tool classes that do not have it.
                            # Only attempt to extract parameters if the tool has a 'function' attribute and it is not None.
                            function_obj = getattr(tool, 'function', None)
                            if function_obj is not None and hasattr(function_obj, 'parameters'):
                                parameters_obj = getattr(
                                    function_obj, 'parameters', None)
                                if parameters_obj is not None and hasattr(parameters_obj, 'properties'):
                                    properties = getattr(
                                        parameters_obj, 'properties', {})
                                    for param_name, param_info in properties.items():
                                        required_list = getattr(
                                            parameters_obj, 'required', [])
                                        tool_info["parameters"][param_name] = {
                                            "type": param_info.get('type', 'unknown'),
                                            "description": param_info.get('description', 'No description'),
                                            "required": param_name in required_list if isinstance(required_list, (list, set, tuple)) else False
                                        }
                            agent_info["tools"].append(tool_info)

            # Extract handoffs
            if isinstance(agent, Agent):
                if hasattr(agent, 'handoffs') and agent.handoffs:
                    for handoff in agent.handoffs:
                        if isinstance(handoff, Handoff):
                            handoff_info = {
                                "name": getattr(handoff, 'name', str(handoff)),
                                "description": getattr(handoff, 'handoff_description', getattr(handoff, 'instructions', 'No description available'))
                            }
                            agent_info["handoffs"].append(handoff_info)

            agent_capabilities[agent_name] = agent_info

        self.agent_capabilities = agent_capabilities

    async def generate_suggested_prompts(self, conversation_input: list[TResponseInputItem], user: User, already_suggested_demo_prompts: List[str] = []) -> Dict[str, List[str]]:
        """
        Generate suggested prompts based on conversation history and available agents/tools.

        Args:
            result: A RunResultStreaming object from running an OpenAI agent

        Returns:
            Dict with 'suggested_prompts' and 'demo_prompts' lists
        """
        # print('Generating suggested prompts')
        # Extract available agents and tools information
        agent_definition = self.agent_capabilities
        # print(agent_definition)

        # available_agents = [agent.name for agent in ORCHESTRATOR_AGENT.handoffs]
        # available_tools = list(ORCHESTRATOR_AGENT.get_all_tools())
        # print(available_tools)
        agent_prompt = f"""
        # Agents, handoffs, and tools:
        {json.dumps(agent_definition, indent=2)}"""

        # Create a comprehensive prompt for the AI
        system_prompt = """You are an AI assistant that analyzes conversations and suggests the most likely next user prompts based on the conversation history and available capabilities."""
        system_prompt += agent_prompt
        system_prompt += """

            Analyze the conversation history and suggest the next most likely user prompts. Consider:
            1. What actions were just performed
            2. What information was retrieved
            3. What natural follow-up actions a user would want
            4. High-probability actions like sending composed emails, replying to emails, saving content, looking up reviews, etc.

            Return up to 3 suggested prompts in order of likelihood, or fewer if there's a very high probability of a single next action.
            Do not suggest similar prompts. Each prompt should result in a different tool being called if it were passed into the defined agent.
            Do not suggest random prompts that are not directly related to the conversation history. Do not feel you need to suggest more than a single prompt that is highly likely and pertinent to the conversation.
            If there is one very high probability action, only return that action.
            ONLY SUGGEST PROMPTS THAT USE AVAILABLE TOOLS. UNDER NO CIRCUMSTANCES SHUOLD YOU SUGGEST PROMPTS THAT DO NOT USE AVAILABLE TOOLS.
            DO NOT SUGGEST MAKING IMAGES OR VISUALS. ONLY SUGGEST PROMPTS THAT USE AVAILABLE TOOLS OR PROMPTS THAT WILL CREATE A TEXT RESPONSE.
            Also calculate the likelihood of each prompt being used based on the conversation history and the available tools. Include the likelihood in the JSON response.
            Heavily weight the liklihood of prompts based upon the most recent response from the assistant.
            Do not exceed 35 characters per prompt. Don't repeat details from the conversation history. Just suggest an action that is likely to be taken next.
            
            IF SOMEONE IS TRYING TO ACCESS ANY GOOGLE SERVICES AND THEY DO NOT HAVE A GOOGLE ACCOUNT CONNECTED, SUGGEST THEY TYPE IN "Connect my Google account" TO CONNECT THEIR GOOGLE ACCOUNT. THIS OVERRIDES ALL OTHER PROMPTS.
            """
        # system_prompt += f"""
        # Already suggested demo prompts: {already_suggested_demo_prompts}
        # Also suggest 3 demo prompts that showcase the available capabilities (not based on conversation history). Do not suggest any prompts that are already in the list of already suggested demo prompts. Randomize which suggest prompts you return and which tools you use. Avoid suggesting any prompts related to travel or weather.
        # """
        system_prompt += """
            Return in this exact JSON format:
            {"suggested_prompts": [{"prompt": "prompt1", "likelihood": "**liklihood as a float between 0 and 1**"}, more prompts with likelihood if appropriate]}"""  # , "demo_prompts": ["demo prompt 1", additonal demo prompts]}}"""

        if user.connected_to_google == True:
            system_prompt += f"""
            This user is connected to Google and can send emails and save documents to Google Docs.
            """
        else:
            system_prompt += """
            This user is not connected to Google and cannot send emails, setup calendar events or save documents to Google Docs.
            """

        if user.connected_to_plaid == True:
            system_prompt += """
            This user is connected to Plaid and can access their bank, credit card, and investment account info.
            """
        else:
            system_prompt += """
            This user is not connected to Plaid and cannot any Plaid related tools or functions.
            """
        # Create the conversation context for the AI
        conversation_text = ""
        previous_prompts = []
        previous_tool_calls = []
        for item in conversation_input:
            if isinstance(item, dict):
                if item.get('role') == 'user':
                    conversation_text = ""
                    conversation_text += f"User: {item.get('content', '')}\n"
                    previous_prompts.append(item.get('content', ''))
                elif item.get('role') == 'assistant':
                    conversation_text += f"Assistant: {item.get('content', '')}\n"
                elif item.get('type') == 'function_call' and 'transfer' not in item.get('name', ''):
                    previous_tool_calls.append(item.get('name', ''))
            else:
                conversation_text += f"System: {str(item)}\n"
        user_prompt = f"""Revent Conversation History:
    {conversation_text}

    Based on this conversation and the available agents/tools, what are the most likely next user prompts?"""

        if len(previous_prompts) > 0:
            user_prompt += f"""
            Previous User Prompts:
            {json.dumps(previous_prompts, indent=2)}
            Do not suggest prompts that are similar to previous user prompts or would give the same information or result in the same tool being called.
            """
        if len(previous_tool_calls) > 0:
            user_prompt += f"""
            Previous Tool Calls:
            {json.dumps(previous_tool_calls, indent=2)}
            Do not suggest prompts that would result in the same tool being called as any previous tool call.
            """

        try:
            # Make the API call
            # print('Making API call')
            response = OPENAI_CLIENT.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=500, response_format={
                    "type": "json_object"
                }
            )
            # print('API call complete')
            # Parse the response
            response_content = response.choices[0].message.content
            # print(response_content)
            # Try to parse as JSON
            try:
                # print('Parsing response')
                result_dict = json.loads(
                    response_content) if response_content is not None else {}
                # print(result_dict)
                # Filter suggested prompts to only include those with likelihood above 0.3
                if len(result_dict.get("suggested_prompts", [])) > 0:
                    highest_likelihood = max(prompt.get(
                        "likelihood", 0) for prompt in result_dict.get("suggested_prompts", []))
                    # result_dict["suggested_prompts"] = [
                    #     prompt for prompt in result_dict.get("suggested_prompts", [])
                    #     if prompt.get("likelihood", 0) > highest_likelihood * 0.5
                    # ]
                    result_dict["suggested_prompts"] = [
                        prompt for prompt in result_dict.get("suggested_prompts", [])
                        if prompt.get("likelihood", 0) > 0.3
                    ]
                # result_dict["suggested_prompts"] = [
                #     prompt for prompt in result_dict.get("suggested_prompts", [])
                #     if prompt.get("likelihood", 0) > 0.3
                # ]
                # print(result_dict['suggested_prompts'])
                # print('Returning result')
                return result_dict.get("suggested_prompts", [])
                # "demo_prompts": result_dict.get("demo_prompts", [])
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                # Fallback if JSON parsing fails
                return {
                    "suggested_prompts": [],
                    "demo_prompts": ["Search for restaurants near me", "Check my email", "Get the price of AAPL"]
                }

        except Exception as e:
            print(f"Error generating suggested prompts: {e}")
            # Return fallback suggestions
            return {
                "suggested_prompts": [],
                "demo_prompts": ["Search for restaurants near me", "Check my email", "Get the price of AAPL"]
            }


async def determine_if_request_handled(conversation_input: list[TResponseInputItem], user: User, chat_id: str, prompt: str) -> bool:
    """Determine if a user's request has been successfully handled.

    Analyzes the conversation history to determine if the most recent user
    request was satisfied. Tracks unhandled requests for product improvement.

    Args:
        conversation_input: List of conversation items (messages, tool calls, etc.)
        user: User object making the request
        chat_id: Chat session identifier
        prompt: The user's original prompt

    Returns:
        tuple: (request_handled, capability_requested, capability_description)
            - request_handled: True if request was satisfied
            - capability_requested: Name of missing capability if unhandled
            - capability_description: Description of missing capability
    """
    system_prompt = """
    You are an AI assistant that looks at a conversation history and determines if the request has been handled to the user's satisfaction.

    Look at the most recent user prompt and determine if the request has been handled to the user's satisfaction.

    Return True if the request has been handled to the user's satisfaction, False otherwise for request_handled.
    Return the capability requested which should be a tool name or handoff name and a description of the capability requested for capability_requested and capability_description.

    Return in this exact JSON format:

    {"request_handled": <boollean>, "capability_requested": <string> or null, "capability_description": <string> or null}
    """

    conversation_text = ""
    previous_prompts = []
    previous_tool_calls = []
    for item in conversation_input:
        if isinstance(item, dict):
            if item.get('role') == 'user':
                conversation_text = ""
                conversation_text += f"User: {item.get('content', '')}\n"
                previous_prompts.append(item.get('content', ''))
            elif item.get('role') == 'assistant':
                conversation_text += f"Assistant: {item.get('content', '')}\n"
            elif item.get('type') == 'function_call' and 'transfer' not in item.get('name', ''):
                previous_tool_calls.append(item.get('name', ''))
        else:
            conversation_text += f"System: {str(item)}\n"

    response = OPENAI_CLIENT.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_text}
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={
            "type": "json_object"
        }
    )

    try:
        response_content = response.choices[0].message.content
        # print(response_content)
        result_dict = json.loads(
            response_content) if response_content is not None else {}
        if not result_dict.get("request_handled", False):
            capability_requested = result_dict.get(
                "capability_requested", None)
            capability_description = result_dict.get(
                "capability_description", None)
            track_unhandled_request(
                user, chat_id, prompt, capability_requested, capability_description)
            return result_dict.get("request_handled", False), capability_requested, capability_description
        return True, None, None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return True, None, None
    except Exception as e:
        print(f"Error determining if request handled: {e}")
        return True, None, None
