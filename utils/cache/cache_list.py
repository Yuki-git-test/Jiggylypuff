ongoing_bidding = set()  # Set of channel_ids that have ongoing bidding
processing_auction_end = (
    set()
)  # Set of channel_ids that are currently processing auction end
processing_roll_back = (
    set()
)  # Set of channel_ids that are currently processing bid roll back
processing_update_ends_on = (
    set()
)  # Set of channel_ids that are currently processing update ends on

auction_cache: dict[int, dict] = {}
# Structure
# auction_cache = {
#     channel_id: {
#         "channel_name": str,
#         "host_id": int,
#         "host_name": str,
#         "pokemon": str,
#         "highest_bidder_id": int,
#         "highest_bidder": str,
#         "highest_offer": int,
#         "autobuy": int,
#         "ends_on": int,  # unix timestamp
#         "accepted_list": str,  # comma separated
#         "image_link": str,
#         "broadcast_msg_id": int,
#         "market_value": int,
#         "minimum_increment": int,
#         "last_minute_pinged": bool,
#         "is_bulk": bool,
#     },
#     ...
# }
market_value_cache: dict[str, dict] = {}

webhook_url_cache: dict[tuple[int, int], dict[str, str]] = {}
#     ...
#
# }
# key = (bot_id, channel_id)
# Structure:
# webhook_url_cache = {
# (bot_id, channel_id): {
#     "url": "https://discord.com/api/webhooks/..."
#     "channel_name": "alerts-channel",
# },
#
