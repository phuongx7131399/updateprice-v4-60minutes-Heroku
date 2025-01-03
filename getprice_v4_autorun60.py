import requests
from notion_client import Client
import schedule
import time

# Tích hợp thông tin API Notion
NOTION_API_KEY = "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"
NOTION_DATABASE_ID = "13a84490908180188122f3e71ab00a1c"

# Kết nối tới Notion
notion = Client(auth=NOTION_API_KEY)

# Hàm lấy toàn bộ dữ liệu từ database Notion (hỗ trợ phân trang)
def get_all_database_items(database_id):
    results = []
    next_cursor = None

    while True:
        query_params = {"database_id": database_id}
        if next_cursor:
            query_params["start_cursor"] = next_cursor
        
        response = notion.databases.query(**query_params)
        results.extend(response["results"])
        
        if response.get("has_more"):
            next_cursor = response["next_cursor"]
        else:
            break

    return results

# Hàm lấy giá và % thay đổi từ CoinGecko
def fetch_prices_from_coingecko(token_ids):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": ",".join(token_ids),
        "price_change_percentage": "1h"  # Lấy % thay đổi trong 1 giờ
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        data = response.json()
        return {item["id"]: item for item in data}
    else:
        print(f"Error fetching prices from CoinGecko: {response.status_code}")
        return {}

# Hàm cập nhật giá token và % thay đổi vào Notion
def update_notion_prices():
    database_items = get_all_database_items(NOTION_DATABASE_ID)
    token_ids = []

    for item in database_items:
        try:
            token_name = item["properties"]["Token"]["title"][0]["text"]["content"].lower()
            token_ids.append(token_name)
        except (KeyError, IndexError):
            print(f"Error processing token data for item: {item}")
            continue

    prices = fetch_prices_from_coingecko(token_ids)

    for item in database_items:
        try:
            token_name = item["properties"]["Token"]["title"][0]["text"]["content"].lower()
            if token_name in prices:
                price = prices[token_name]["current_price"]
                change_1h = prices[token_name].get("price_change_percentage_1h_in_currency", None)

                # Tạo biểu tượng hiển thị tăng/giảm
                if change_1h is not None:
                    if change_1h > 0:
                        visual_change = f"🟢⬆️ {round(change_1h, 2)}%"
                    elif change_1h < 0:
                        visual_change = f"🔴⬇️ {round(change_1h, 2)}%"
                    else:
                        visual_change = "⏺️ 0%"
                else:
                    visual_change = "N/A"

                update_data = {
                    "Price": {
                        "number": price
                    },
                    "Change 1h Visual": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": visual_change
                                }
                            }
                        ]
                    }
                }

                notion.pages.update(
                    page_id=item["id"],
                    properties=update_data
                )
                print(f"Updated {token_name} with price {price} and visual change {visual_change}")
            else:
                print(f"No price data found for {token_name}")
        except KeyError as e:
            print(f"Error updating price for token: {e}")

# Hàm chạy tự động
def job():
    print("Running scheduled job...")
    update_notion_prices()

# Đặt lịch chạy mỗi 60 phút
schedule.every(60).minutes.do(job)

# Vòng lặp để giữ cho chương trình chạy liên tục
if __name__ == "__main__":
    print("Scheduler started. Waiting for the next job...")
    while True:
        schedule.run_pending()
        time.sleep(1)
