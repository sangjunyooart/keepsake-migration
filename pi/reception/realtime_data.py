"""
Realtime environmental data feeds for exhibition phase.

PLACEHOLDER — not yet implemented.
Populated during Plexus residency (July 2026) with Seungho Lee.

Expected data types per lens:
  environmental_time  : live weather / air quality at exhibition site
  human_time          : crowd density, activity rhythms
  digital_time        : network traffic, social media pulse
  infrastructure_time : local infrastructure status
  liminal_time        : TBD with Seungho
  more_than_human_time: ambient bioacoustic data, light levels

Interface (to be implemented):
  get_current(lens_name: str) -> dict
    Returns latest environmental snapshot, or {} if unavailable.
"""
import logging

logger = logging.getLogger(__name__)


def get_current(lens_name: str) -> dict:
    """
    Return the latest environmental data for this lens.
    Currently returns empty dict — placeholder for exhibition phase.
    """
    logger.debug("realtime_data.get_current called for %s (placeholder)", lens_name)
    return {}
