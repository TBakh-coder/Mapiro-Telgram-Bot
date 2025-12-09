# Mapiro-Telgram-Bot
This is Mapiro Telegram bot created by Bakhtiyar Aghayev

# 📍 Nearby Place Finder Telegram Bot

A Telegram bot built with Python that uses the **Google Places API (New)** to find nearby facilities and points of interest based on the user's current location and a specified search radius.

## ✨ Features

* **Location-Based Search:** Requests and uses the user's Telegram location to center the search.
* **Flexible Radius:** Allows the user to select from predefined search radii (500m, 1km, etc.) or input a custom radius.
* **Category Search:** Provides buttons for common facility types (Restaurants, Cafes, Hospitals, etc.).
* **Custom Text Search:** Supports open-ended queries (e.g., "sushi restaurant," "best barbers").
* **Place Details:** Displays place name, address, rating, a review snippet (if available), and calculated distance.
* **Photos & Directions:** Sends the first available photo and provides an inline button for Google Maps directions.
* **Pagination:** Supports fetching more search results via an inline button.

## 🛠 Prerequisites

* Python 3.8+
* A Telegram Bot Token (from BotFather)
* A Google Cloud Project with the **Places API (New)** enabled and a valid **API Key**.

## 🚀 Setup and Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Create API Key Files:**
    The bot requires two files in the root directory to store your credentials:
    * **`BOT_TOKEN`**: Create this file and paste your Telegram Bot Token inside.
        ```
        # BOT_TOKEN
        123456789:AABBCCddeeffGgHhIiJjKkLlMmNnOoPp
        ```
    * **`MAPS_TOKEN`**: Create this file and paste your Google API Key inside.
        ```
        # MAPS_TOKEN (Your Google API Key)
        AIzaSy...
        ```

4.  **Run the bot:**
    ```bash
    python your_script_name.py
    ```
    (Replace `your_script_name.py` with the actual name of your main Python file).

## ⚠️ Important API Notes

This bot is designed to use the **Places API (New)** (version 1). Ensure that the following are enabled in your Google Cloud Project:
* **Places API (New)**
* **Maps Static API** (This is needed for the directions link to work correctly, as it often falls back to the old Google Maps URL structure.)
* Review Google's pricing for the Places API (New) as usage will incur costs based on the data fields requested.

## 📝 License

This project is licensed under the **MIT License**.
