from agents.extensions.handoff_prompt import RECOMMENDED_PROMPT_PREFIX
from agents import Agent, function_tool, RunContextWrapper
from easypost.easypost_client import EasyPostClient
from .gmail import GMAIL_AGENT
from .google_docs import GOOGLE_DOCS_AGENT
try:
    from config import Settings
except ImportError:
    from ..config import Settings
try:
    from firebase import EasyPostTracker
except ImportError:
    from ..firebase import EasyPostTracker
from .utils.context import ChatContext
from .utils.responses import ToolResponse

SETTINGS = Settings()

EASYPOST_CLIENT = EasyPostClient(api_key=SETTINGS.easypost_api_key)


@function_tool
def get_tracking_info_with_easypost(wrapper: RunContextWrapper[ChatContext], tracking_number: str) -> dict:
    """Get real-time tracking information for a package.

    Args:
        wrapper: Execution context with user authentication
        tracking_number: Carrier tracking number (USPS, UPS, FedEx, DHL, etc.)
    Returns:
        ToolResponse with tracking status, location history, and delivery info
    """
    existing_tracker = EasyPostTracker.get_tracker_by_tracking_number(
        tracking_number)
    # print(existing_tracker)
    # print(tracking_number)
    if existing_tracker:
        tracking_info = EASYPOST_CLIENT.tracker.retrieve(
            existing_tracker.easypost_id)
        return ToolResponse(
            response_type="easypost_tracking_info",
            agent_name="EasyPost",
            friendly_name="EasyPostTracking Info",
            display_response=True,
            response=tracking_info.to_dict()
        ).to_dict()
    else:
        tracking_info = EASYPOST_CLIENT.tracker.create(
            tracking_code=tracking_number)
        # print(tracking_info)
        EasyPostTracker.create_tracker(
            wrapper.context.user, tracking_number, tracking_info.carrier, tracking_info.id)
        return ToolResponse(
            response_type="easypost_tracking_info",
            agent_name="EasyPost",
            friendly_name="EasyPostTracking Info",
            display_response=True,
            response=tracking_info.to_dict()
        ).to_dict()


@function_tool
def get_all_packages_with_easypost(wrapper: RunContextWrapper[ChatContext]) -> dict:
    """Get tracking info for all saved packages.

    Args:
        wrapper: Execution context with user authentication
    Returns:
        ToolResponse with list of all tracked packages and their current status
    """
    packages = EasyPostTracker.get_trackers_by_user_id(
        wrapper.context.user.reference_id)
    package_info = []
    for package in packages:
        tracking_info = EASYPOST_CLIENT.tracker.retrieve(package.easypost_id)
        package_info.append(tracking_info.to_dict())
    return ToolResponse(
        response_type="easypost_all_packages",
        agent_name="EasyPost",
        friendly_name="All Stored Packages",
        display_response=True,
        response=package_info
    ).to_dict()


EASYPOST_AGENT = Agent(
    name="EasyPost",
    model="gpt-4o",
    handoff_description=RECOMMENDED_PROMPT_PREFIX + "Package tracking via EasyPost.",
    instructions=RECOMMENDED_PROMPT_PREFIX +
    "Track packages from all major carriers with real-time status updates.",
    tools=[get_tracking_info_with_easypost, get_all_packages_with_easypost],
    handoffs=[GOOGLE_DOCS_AGENT, GMAIL_AGENT]
)

ALL_TOOLS = [get_tracking_info_with_easypost, get_all_packages_with_easypost]
