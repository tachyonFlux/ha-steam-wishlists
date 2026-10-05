# Steam Wishlists for Home Assistant

A custom integration that pulls your game's wishlist numbers from the Steamworks partner API and exposes them as Home Assistant sensors, so you can build a dashboard card and fire automations on wishlist spikes.

This is an unofficial project and is not affiliated with or endorsed by Valve.

![Wishlist card](docs/card.png)

## Features

- Daily wishlist adds, deletes, purchases and gifts, pulled straight from Steamworks
- A running **total** wishlist count, derived from your full history
- Net change for the last day and the last 7 days
- Full history kept as a chart-ready attribute, so graphs are populated immediately instead of starting empty
- UI config flow — no YAML, no API key in your `configuration.yaml`
- History cached locally, so restarts don't re-download everything

## Requirements

- A game on Steam with access to the Steamworks partner site
- A **Financial API Group** key (a regular Steam Web API key will not work — see below)
- Home Assistant 2025.2 or newer
- [apexcharts-card](https://github.com/RomRider/apexcharts-card) via HACS, for the example graph

## Getting a Financial API key

The wishlist endpoint lives under `IPartnerFinancialsService`, which needs its own key:

1. In Steamworks, go to **Users & Permissions → Manage Groups**.
2. Create a group and mark it as a **Financial API Group**.
3. Open the group's page and copy the Web API key shown there.
4. Optionally whitelist the IPs allowed to use the key. If you do, include the public IP of your Home Assistant instance — a changing home IP is a common cause of sudden auth failures.

Treat this key as a secret. It can read your sales and financial reporting, not just wishlists.

## Installation

### HACS (recommended)

1. HACS → **Custom repositories** → add this repo's URL, type **Integration**.
2. Install **Steam Wishlists**, then restart Home Assistant.

### Manual

Copy `custom_components/steam_wishlist/` into your Home Assistant `config/custom_components/` directory and restart.

## Setup

**Settings → Devices & Services → Add Integration → Steam Wishlists**, then provide:

| Field | Notes |
| --- | --- |
| Name | Device name; controls the entity ids. Default `Steam wishlists`. |
| Financial API key | From the Financial API Group above. |
| App ID | Your game's Steam app id. |
| Start date | The day your store page went live. Data before this doesn't exist. |

Setup test-fetches yesterday, so a bad key or blocked IP fails right away with a clear error.

On first run the integration backfills your history at up to 45 days per refresh, polling every 30 seconds until it has caught up, then settles into its normal interval. A year of history takes a few minutes in the background.

### Options

Open **Configure** on the integration to change:

- **Hours between checks** (default 3). Valve publishes once a day at an unspecified time, so checking a few times a day picks up new data soon after it lands. Polling faster won't produce intraday numbers — there aren't any.
- **Days of history for the chart** (default 90). This controls the size of the `series` attribute on the total sensor.

## Entities

With the default name:

| Entity | Meaning |
| --- | --- |
| `sensor.steam_wishlists_total` | Running total wishlists |
| `sensor.steam_wishlists_net` | Net change on the most recent day |
| `sensor.steam_wishlists_net_7d` | Net change over the last 7 days |
| `sensor.steam_wishlists_adds` | Adds on the most recent day |
| `sensor.steam_wishlists_deletes` | Deletes on the most recent day |

The total sensor also carries two attributes: `last_date` and `series`, a list of `[date, running_total, daily_net]` entries. The other sensors deliberately carry no attributes, to keep the recorder database small.

The total is computed as `adds - deletes - purchases - gifts`, since a purchase or a received gift also removes the game from a wishlist. Compare it with your Steamworks dashboard once to confirm it lines up for your title.

## Dashboard card

See [`lovelace-card.yaml`](lovelace-card.yaml) for a stats-plus-graph card: four tiles over a chart with the running total as a line and daily net change as columns. Keep `graph_span` in sync with the chart days option.

## Automation example

```yaml
triggers:
  - trigger: numeric_state
    entity_id: sensor.steam_wishlists_net
    above: 50
actions:
  - action: notify.notify
    data:
      message: "Wishlist spike: +{{ states('sensor.steam_wishlists_net') }} yesterday"
```

## Troubleshooting

**Every day returns zero.** Date formats differ between Steamworks endpoints. Change `day.isoformat()` in `coordinator.py` to `day.strftime("%Y/%m/%d")` and reload.

**Auth errors after it was working.** Most often an IP whitelist on the key plus a changed home IP. Update the whitelist, or remove it and rely on key secrecy.

**The total doesn't match Steamworks.** Check that your start date isn't later than your store page launch — any days before it are missing from the sum.

**Numbers look a day behind.** Expected. The API publishes the previous day's data, so the most recent day shown is always yesterday.

## Notes and limits

- The API returns one day per request, which is why history is backfilled and cached rather than fetched on demand.
- Country and language breakdowns are available in the API response but aren't exposed as entities yet.
- Data is cached in `.storage/steam_wishlist_<appid>`. Delete that file to force a full re-fetch.

## License

MIT
