"""Config and options flow for the Steam Wishlists integration."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    ConfigEntry,
)
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import selector

from .const import (
    API_URL,
    CONF_APPID,
    CONF_CHART_DAYS,
    CONF_POLL_HOURS,
    CONF_START_DATE,
    DEFAULT_CHART_DAYS,
    DEFAULT_NAME,
    DEFAULT_POLL_HOURS,
    DOMAIN,
)

SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
        vol.Required(CONF_API_KEY): str,
        vol.Required(CONF_APPID): selector.NumberSelector(
            selector.NumberSelectorConfig(min=1, mode=selector.NumberSelectorMode.BOX)
        ),
        vol.Required(CONF_START_DATE): selector.DateSelector(),
    }
)


class SteamWishlistConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ask for the Financial API key, app id and store-page start date."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            appid = int(user_input[CONF_APPID])
            await self.async_set_unique_id(str(appid))
            self._abort_if_unique_id_configured()
            errors = await self._validate(user_input[CONF_API_KEY], appid)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_APPID: appid,
                        CONF_START_DATE: user_input[CONF_START_DATE],
                    },
                )
        return self.async_show_form(step_id="user", data_schema=SCHEMA, errors=errors)

    async def _validate(self, key: str, appid: int) -> dict[str, str]:
        session = async_get_clientsession(self.hass)
        day = (date.today() - timedelta(days=1)).isoformat()
        params = {"key": key, "appid": str(appid), "date": day}
        try:
            async with session.get(
                API_URL, params=params, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status in (401, 403):
                    return {"base": "invalid_auth"}
                resp.raise_for_status()
                payload = await resp.json(content_type=None)
        except aiohttp.ClientError:
            return {"base": "cannot_connect"}
        if "response" not in payload:
            return {"base": "unexpected_response"}
        return {}

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return SteamWishlistOptionsFlow()


class SteamWishlistOptionsFlow(OptionsFlow):
    """Polling frequency and how much history the chart attribute carries."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_POLL_HOURS,
                    default=options.get(CONF_POLL_HOURS, DEFAULT_POLL_HOURS),
                ): vol.All(vol.Coerce(float), vol.Range(min=1, max=24)),
                vol.Required(
                    CONF_CHART_DAYS,
                    default=options.get(CONF_CHART_DAYS, DEFAULT_CHART_DAYS),
                ): vol.All(vol.Coerce(int), vol.Range(min=7, max=730)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
