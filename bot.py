import httpx
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters, CallbackQueryHandler
import math
import uuid
import os

# --- Configuration ---

# BOT_TOKEN of Python here
BOT_TOKEN_FILE = "BOT_TOKEN"

try:
    with open(BOT_TOKEN_FILE, "r") as f:
        BOT_TOKEN = f.read().strip()
    if not BOT_TOKEN:
        raise ValueError(f"Bot token file '{BOT_TOKEN_FILE}' is empty.")
    print("Bot token loaded successfully.")
except FileNotFoundError:
    print(f"Error: Bot token file '{BOT_TOKEN_FILE}' not found. Please create it and put your bot token inside.")
    exit(1)
except Exception as e:
    print(f"Error loading bot token: {e}")
    exit(1)

# Load GOOGLE_API_KEY from a file named MAPS_TOKEN
MAPS_TOKEN_FILE = "MAPS_TOKEN"

try:
    with open(MAPS_TOKEN_FILE, "r") as f:
        GOOGLE_API_KEY = f.read().strip()
    if not GOOGLE_API_KEY:
        raise ValueError(f"Google API key file '{MAPS_TOKEN_FILE}' is empty.")
    print("Google API key (from MAPS_TOKEN) loaded successfully.")
except FileNotFoundError:
    print(f"Error: Google API key file '{MAPS_TOKEN_FILE}' not found. Please create it and put your Google API key inside.")
    exit(1)
except Exception as e:
    print(f"Error loading Google API key from '{MAPS_TOKEN_FILE}': {e}")
    exit(1)


# --- Constants and Mappings ---

# Facility type mapping. 'custom_query_trigger' is a placeholder to handle the button press.
FACILITY_TYPES = {
    "🍽 Restaurants": "restaurant",
    "☕ Cafes": "cafe",
    "🛍 Shops": "store",
    "🏪 Convenience Stores": "convenience_store",
    "🏨 Hotels": "lodging",
    "🏥 Hospitals": "hospital",
    "💊 Pharmacies": "pharmacy",
    "⛽ Gas Stations": "gas_station",
    "🚗 Parking": "parking",
    "🏦 Banks/ATMs": "atm",
    "🚇 Metro Stations": "subway_station",
    "🚍 Bus Stops": "bus_station",
    "🎓 Schools": "school",
    "🕌 Worship Places": "place_of_worship",
    "✍️ Custom Query": "custom_query_trigger", # Trigger for custom text search state
}

# Default search radius in meters
DEFAULT_RADIUS = 500.0

# Earth's radius in kilometers
EARTH_RADIUS_KM = 6371.0

# --- Helper Functions for Keyboards ---

def create_radius_keyboard():
    """Creates a ReplyKeyboardMarkup for selecting search radius."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("500m"), KeyboardButton("1000m")],
            [KeyboardButton("2000m"), KeyboardButton("5000m")],
            [KeyboardButton("🔙 Stop / Back")],
            [KeyboardButton("/clear")]
        ],
        resize_keyboard=True
    )

def create_facility_keyboard():
    """Creates a ReplyKeyboardMarkup for choosing facility types or custom query."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🍽 Restaurants"), KeyboardButton("☕ Cafes")],
            [KeyboardButton("🛍 Shops"), KeyboardButton("🏪 Convenience Stores")],
            [KeyboardButton("🏨 Hotels"), KeyboardButton("🏥 Hospitals")],
            [KeyboardButton("💊 Pharmacies"), KeyboardButton("⛽ Gas Stations")],
            [KeyboardButton("🚗 Parking"), KeyboardButton("🏦 Banks/ATMs")],
            [KeyboardButton("🚇 Metro Stations"), KeyboardButton("🚍 Bus Stops")],
            [KeyboardButton("🎓 Schools"), KeyboardButton("🕌 Worship Places")],
            [KeyboardButton("✍️ Custom Query")], # New button for custom search
            [KeyboardButton("🔙 Stop / Back")],
            [KeyboardButton("/clear")],
        ],
        resize_keyboard=True
    )

def get_place_photo_url(photo_name, max_width=800, max_height=600):
    """
    Constructs the URL for a Google Place Photo.
    'photo_name' is the resource name from Places API V1.
    """
    return (
        f"https://places.googleapis.com/v1/{photo_name}/media"
        f"?key={GOOGLE_API_KEY}"
        f"&maxWidthPx={max_width}"
        f"&maxHeightPx={max_height}"
    )

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points on Earth using the Haversine formula.
    Returns distance in kilometers.
    """
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)

    # Haversine formula
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = EARTH_RADIUS_KM * c
    return distance

# --- Global Stop/Back Handler ---
async def stop_back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the 'Stop / Back' button across all states."""
    print("DEBUG: stop_back_handler called.")
    context.user_data.clear() # Clear all user data to reset the conversation
    keyboard = [[KeyboardButton("Send location 📍", request_location=True)]]
    await update.message.reply_text(
        "🛑 Stopped. You can start again by sending your location:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )
    return


# --- Bot Commands and Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command, clears user data, and requests location."""
    context.user_data.clear()
    keyboard = [[KeyboardButton("Send location 📍", request_location=True)]]
    await update.message.reply_text(
        "Welcome! Please share your **current location** to find nearby places:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /clear command, resetting user data and conversation state."""
    context.user_data.clear()
    keyboard = [[KeyboardButton("Send location 📍", request_location=True)]]
    await update.message.reply_text(
        "🗑️ **Chat data cleared and conversation reset.**\n\n"
        "Please send your **current location** to find nearby places:",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True),
        parse_mode='Markdown'
    )


async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles incoming location data, stores it, and prompts for search radius."""
    lat = update.message.location.latitude
    lon = update.message.location.longitude
    context.user_data['lat'] = lat
    context.user_data['lon'] = lon
    context.user_data['current_state'] = 'awaiting_radius' # Set bot's state

    await update.message.reply_text(
        f"Location received: `{lat}, {lon}`\n\n"
        "Please choose a **search radius** or type a custom one (in meters):",
        reply_markup=create_radius_keyboard(),
        parse_mode='Markdown'
    )

async def call_google_places_nearby_search(lat, lon, place_type, radius, page_token=None):
    """
    Calls the Google Places API (New) 'searchNearby' endpoint for type-based searches.
    """
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,"
            "places.formattedAddress,"
            "places.rating,"
            "places.userRatingCount,"
            "places.reviews,"
            "places.location,"
            "places.id,"
            "places.photos"
        )
    }
    payload = {
        "includedTypes": [place_type],
        "maxResultCount": 10,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": float(radius)
            }
        }
    }
    if page_token:
        payload['pageToken'] = page_token

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()

async def call_google_places_text_search(lat, lon, text_query, radius, page_token=None):
    """
    Calls the Google Places API (New) 'searchText' endpoint for custom text queries.
    Uses locationBias for proximity.
    """
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": GOOGLE_API_KEY,
        "X-Goog-FieldMask": (
            "places.displayName,"
            "places.formattedAddress,"
            "places.rating,"
            "places.userRatingCount,"
            "places.reviews,"
            "places.location,"
            "places.id,"
            "places.photos"
        )
    }
    # Note: SearchText uses locationBias, not a hard restriction,
    # so we will filter results manually later. We use the given radius as the bias.
    payload = {
        "textQuery": text_query,
        "maxResultCount": 10,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lon},
                "radius": float(radius)
            }
        }
    }
    if page_token:
        payload['pageToken'] = page_token

    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=30.0)
        response.raise_for_status()
        return response.json()


async def radius_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user's radius input (from button or text)."""
    user_text = update.message.text
    lat = context.user_data.get("lat")
    lon = context.user_data.get("lon")

    if not lat or not lon:
        await update.message.reply_text("❗ Please share your location first using /start.")
        return

    radius = DEFAULT_RADIUS

    try:
        if user_text.endswith("m"):
            radius = float(user_text[:-1])
        else:
            radius = float(user_text)
        if radius <= 0:
            raise ValueError("Radius must be a positive number.")
    except ValueError:
        await update.message.reply_text(
            "❗ Invalid radius. Please enter a number (in meters) or choose from the buttons. "
            f"Using default radius of `{int(DEFAULT_RADIUS)}m` for now.",
            parse_mode='Markdown'
        )
        radius = DEFAULT_RADIUS

    context.user_data['radius'] = radius
    context.user_data['current_state'] = 'awaiting_facility_type' # Set to main menu state
    context.user_data.pop('next_page_token', None)
    context.user_data.pop('temp_place_data', None)

    await update.message.reply_text(
        f"Search radius set to `{int(radius)}m`.\n\n"
        "**Choose a facility type or press '✍️ Custom Query' for specific places:**", # Updated text
        reply_markup=create_facility_keyboard(),
        parse_mode='Markdown'
    )


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles inline keyboard button presses (e.g., 'More Results', 'Get Directions')."""
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    if callback_data == "more_results":
        lat = context.user_data.get("lat")
        lon = context.user_data.get("lon")
        radius = context.user_data.get("radius", DEFAULT_RADIUS)
        search_mode = context.user_data.get("search_mode")
        search_param = context.user_data.get("search_param")
        next_page_token = context.user_data.get('next_page_token')

        if not lat or not lon or not search_mode or not search_param or not next_page_token:
            await query.edit_message_text("❗ Cannot fetch more results. Please start a new search.")
            return

        await query.message.reply_text("Fetching more results...")
        await execute_search_and_send_results(query, context)

    elif callback_data.startswith("get_directions_"):
        short_id = callback_data.split('_')[2]
        place_data = context.user_data.get('temp_place_data', {}).get(short_id)

        if not place_data:
            await query.message.reply_text("❗ Sorry, I couldn't find the details for directions. Please try searching again.")
            return

        dest_lat = place_data.get('lat')
        dest_lon = place_data.get('lon')
        place_id = place_data.get('place_id')
        user_lat = context.user_data.get("lat")
        user_lon = context.user_data.get("lon")


        if not dest_lat or not dest_lon or not place_id or not user_lat or not user_lon:
            await query.message.reply_text("❗ Missing destination or origin information for directions.")
            return

        directions_url = (
            f"https://www.google.com/maps/dir/?api=1&origin={user_lat},{user_lon}"
            f"&destination={dest_lat},{dest_lon}&destination_place_id={place_id}&travelmode=driving"
        )

        await query.message.reply_text(
            f"Click here for directions: [Google Maps Directions]({directions_url})",
            parse_mode='Markdown',
            disable_web_page_preview=True
        )

async def execute_search_and_send_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Centralized function to perform the Google Places API search
    (either searchNearby or searchText) and then send the results.
    """
    lat = context.user_data.get("lat")
    lon = context.user_data.get("lon")
    radius = context.user_data.get("radius", DEFAULT_RADIUS)
    search_mode = context.user_data.get("search_mode")
    search_param = context.user_data.get("search_param")
    page_token = context.user_data.get("next_page_token")

    if not lat or not lon:
        await update.effective_chat.send_message("❗ Location data is missing. Please start a new search using /start.")
        return

    if not search_mode or not search_param:
        await update.effective_chat.send_message(
            "❗ Search parameters are missing. Please choose a facility type or enter a query again."
        )
        context.user_data['current_state'] = 'awaiting_facility_type'
        await update.effective_chat.send_message(
            "Please choose a **facility type**:",
            reply_markup=create_facility_keyboard(),
            parse_mode='Markdown'
        )
        return

    places = []
    try:
        if search_mode == 'type_based':
            # Nearby Search uses radius as a hard filter
            data = await call_google_places_nearby_search(lat, lon, search_param, radius, page_token)
        elif search_mode == 'text_based':
            # Text Search uses radius as a bias, so we must filter results manually below
            data = await call_google_places_text_search(lat, lon, search_param, radius, page_token)
        else:
            await update.effective_chat.send_message("❗ Invalid search mode detected. Please start a new search.")
            return

        all_places = data.get("places", [])
        context.user_data['next_page_token'] = data.get("nextPageToken")

        # --- Distance Filtering Implementation ---
        # Filter places based on the exact radius selected by the user.
        # Places API returns distance in meters, calculate_distance returns in km.
        radius_km = radius / 1000.0

        for place in all_places:
            location = place.get("location", {})
            place_lat = location.get("latitude")
            place_lon = location.get("longitude")

            if place_lat and place_lon:
                dist_km = calculate_distance(lat, lon, place_lat, place_lon)
                # Only include the place if its distance is within the specified radius (in km)
                if dist_km * 1000 <= radius + 10: # Add a small buffer (10m) for calculation accuracy
                    places.append(place)
        # ----------------------------------------

    except httpx.HTTPStatusError as e:
        error_message = f"❌ Error from Google Places API: {e.response.status_code} - {e.response.text}"
        await update.effective_chat.send_message(error_message)
        return
    except httpx.RequestError as e:
        error_message = f"❌ Network error: Could not connect to Google Places API. Details: {e}"
        await update.effective_chat.send_message(error_message)
        return
    except Exception as e:
        error_message = f"An unexpected error occurred during search: {e}"
        await update.effective_chat.send_message(error_message)
        return

    await send_places_results(update, context, places, page_token)


async def send_places_results(update: Update, context: ContextTypes.DEFAULT_TYPE, places, page_token):
    """
    Formats and sends the places results to the user, one message per place.
    Includes distance calculation.
    """
    if not places:
        if not page_token:
            await update.effective_chat.send_message("No nearby places found 😞. Try a different radius or facility type/query.")
        else:
            await update.effective_chat.send_message("No more results found 😞.")
        return

    if not page_token:
        context.user_data['temp_place_data'] = {}

    user_lat = context.user_data.get("lat")
    user_lon = context.user_data.get("lon")

    for place in places:
        name = place.get("displayName", {}).get("text", "Unnamed")
        address = place.get("formattedAddress", "Address not available")
        rating = place.get("rating", "N/A")
        rating_count = place.get("userRatingCount", 0)
        reviews = place.get("reviews", [])
        location = place.get("location", {})
        place_lat = location.get("latitude")
        place_lon = location.get("longitude")
        place_id = place.get("id")
        photos = place.get("photos", [])

        comment = f'💬 "{reviews[0]["text"]["text"]}"' if reviews else ""

        distance_info = ""
        if user_lat and user_lon and place_lat and place_lon:
            dist_km = calculate_distance(user_lat, user_lon, place_lat, place_lon)
            if dist_km < 1.0:
                distance_info = f"~{int(dist_km * 1000)} meters away"
            else:
                distance_info = f"~{dist_km:.2f} km away"

        place_message_caption = (
                f"• *{name}*\n"
                f"⭐ {rating}" + (f" ({rating_count} reviews)" if rating_count > 0 else "") + "\n"
                                                                                             f"{comment}\n"
                                                                                             f"📍 {address}\n"
                                                                                             f"📏 {distance_info}\n"
        )

        inline_keyboard_buttons = []
        if place_lat and place_lon and place_id:
            short_id = str(uuid.uuid4())[:8]
            context.user_data['temp_place_data'][short_id] = {
                'lat': place_lat,
                'lon': place_lon,
                'place_id': place_id,
                'name': name
            }
            inline_keyboard_buttons.append(
                [InlineKeyboardButton(
                    f"🚶‍♂️ Get Directions",
                    callback_data=f"get_directions_{short_id}"
                )]
            )

        reply_markup = InlineKeyboardMarkup(inline_keyboard_buttons)

        photo_url = None
        if photos:
            first_photo_name = photos[0].get('name')
            if first_photo_name:
                photo_url = get_place_photo_url(first_photo_name)

        if photo_url:
            await update.effective_chat.send_photo(
                photo=photo_url,
                caption=place_message_caption,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_notification=False
            )
        else:
            await update.effective_chat.send_message(
                place_message_caption,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )

    if context.user_data.get('next_page_token'):
        more_results_keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("➡️ More Results", callback_data="more_results")]]
        )
        await update.effective_chat.send_message(
            "Load more results:",
            reply_markup=more_results_keyboard
        )

# --- Main Bot Setup ---

def main():
    """Starts the bot."""
    if not BOT_TOKEN or not GOOGLE_API_KEY:
        print("Required API keys/tokens not loaded. Exiting.")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_command))

    # IMPORTANT: Add the global stop_back_handler *before* the text_message_router
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex("^🔙 Stop / Back$"), stop_back_handler))

    # Message handlers
    app.add_handler(MessageHandler(filters.LOCATION, location_handler))

    # This router dispatches other text messages based on the bot's current state
    async def text_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message.text == "/clear":
            await clear_command(update, context)
            return

        user_text = update.message.text
        current_state = context.user_data.get('current_state')

        if current_state == 'awaiting_radius':
            await radius_handler(update, context)

        elif current_state == 'awaiting_facility_type':

            # 1. Check if the text matches a known facility type button (including the custom query trigger)
            if user_text in FACILITY_TYPES:
                # 1a. User pressed a standard category button (Type-based search)
                if FACILITY_TYPES[user_text] != 'custom_query_trigger':
                    context.user_data['search_mode'] = 'type_based'
                    context.user_data['search_param'] = FACILITY_TYPES[user_text]
                    context.user_data['current_state'] = 'displaying_results'
                    await update.message.reply_text(f"🔎 Searching for nearby *{user_text}*...", parse_mode='Markdown')
                    # Reset pagination and execute search
                    context.user_data['next_page_token'] = None
                    context.user_data['temp_place_data'] = {}
                    await execute_search_and_send_results(update, context)

                # 1b. User pressed the Custom Query button (State transition)
                else: # FACILITY_TYPES[user_text] == 'custom_query_trigger'
                    context.user_data['current_state'] = 'awaiting_custom_query'
                    await update.message.reply_text(
                        "📝 Please **type your custom search query** now (e.g., `Biedronka`, `sushi restaurant`, `best barbers`):",
                        reply_markup=ReplyKeyboardMarkup([
                            [KeyboardButton("🔙 Stop / Back")],
                            [KeyboardButton("/clear")]
                        ], resize_keyboard=True),
                        parse_mode='Markdown'
                    )
            else:
                await update.message.reply_text(
                    "❗ Invalid choice. Please select a category button or use the '✍️ Custom Query' button to search for specific places."
                )

        elif current_state == 'awaiting_custom_query':
            # User is typing their search query (Text-based search)
            query = user_text.strip()
            if query:
                context.user_data['search_mode'] = 'text_based'
                context.user_data['search_param'] = query
                context.user_data['current_state'] = 'displaying_results'
                await update.message.reply_text(f"🔎 Searching for *'{query}'*...", parse_mode='Markdown')

                # Reset pagination data and execute search
                context.user_data['next_page_token'] = None
                context.user_data['temp_place_data'] = {}
                await execute_search_and_send_results(update, context)
            else:
                await update.message.reply_text("❗ Please enter a non-empty search query.")

        else:
            await update.message.reply_text(
                "I'm not sure what you mean. Please use the provided buttons or type /start to begin."
            )

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_router))

    # Callback query handler for inline keyboard buttons
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    print("Bot started polling...")
    app.run_polling(poll_interval=1.0)

if __name__ == '__main__':
    main()