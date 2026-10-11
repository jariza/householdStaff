from langchain_core.tools import tool

@tool
def turn_on_garden_light(zone: str) -> str:
    """Turns on the lights in a specific area of the garden."""
    print(f"\n💡 [GARDEN TOOL] Turning on lights in: {zone}...\n")
    return f"The lights in the '{zone}' area of the garden are turned on."