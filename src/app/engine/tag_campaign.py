"""TAG campaign shell — persistent settlement/downtime state (TAG p.9–15)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..db import now_utc
from ..schemas import CampaignState, SessionState
from .abyss_tables import is_abyss_profile

if TYPE_CHECKING:
    from ..db import Store

DEFAULT_CAMPAIGN_ID = "default"


def default_campaign() -> CampaignState:
    timestamp = now_utc()
    return CampaignState(
        id=DEFAULT_CAMPAIGN_ID,
        tag_banking_enabled=False,
        days_passed=0,
        adventures_completed=0,
        created_at=timestamp,
        updated_at=timestamp,
    )


def load_campaign(store: Store) -> CampaignState:
    campaign = store.get("campaigns", DEFAULT_CAMPAIGN_ID, CampaignState.model_validate)
    if campaign is None:
        campaign = default_campaign()
        store.save("campaigns", campaign)
    return campaign


def save_campaign(store: Store, campaign: CampaignState) -> CampaignState:
    campaign.updated_at = now_utc()
    store.save("campaigns", campaign)
    return campaign


def apply_abyss_campaign_to_session(store: Store, session: SessionState) -> SessionState:
    if not is_abyss_profile(session):
        return session
    campaign = load_campaign(store)
    if campaign.abyss_campaign_plot is not None:
        plot = campaign.abyss_campaign_plot.model_copy(deep=True)
        if not plot.completed:
            plot.entity_piece_claimed_this_adventure = False
            session.abyss_campaign_plot = plot
    if campaign.abyss_vampire_sire is not None:
        session.abyss_vampire_sire = campaign.abyss_vampire_sire.model_copy(deep=True)
    return session


def sync_abyss_campaign_from_session(store: Store, session: SessionState) -> CampaignState:
    campaign = load_campaign(store)
    if not is_abyss_profile(session):
        return campaign
    plot = session.abyss_campaign_plot
    if plot is not None:
        copied = plot.model_copy(deep=True)
        if copied.completed:
            already_recorded = any(
                existing.key == copied.key
                and existing.completed
                and existing.progress == copied.progress
                and existing.final_bosses_defeated == copied.final_bosses_defeated
                and existing.gold_contributed == copied.gold_contributed
                and existing.artifact_clues_spent == copied.artifact_clues_spent
                for existing in campaign.abyss_campaign_completed_plots
            )
            if not already_recorded:
                campaign.abyss_campaign_completed_plots.append(copied)
            campaign.abyss_campaign_plot = None
        else:
            campaign.abyss_campaign_plot = copied
    campaign.abyss_vampire_sire = (
        session.abyss_vampire_sire.model_copy(deep=True)
        if session.abyss_vampire_sire is not None
        else None
    )
    return save_campaign(store, campaign)


def record_adventure_complete(store: Store) -> CampaignState:
    campaign = load_campaign(store)
    campaign.adventures_completed += 1
    campaign.days_passed += 1
    return save_campaign(store, campaign)
