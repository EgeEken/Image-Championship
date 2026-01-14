import os
import random
import json
import base64
from pathlib import Path
import pandas as pd
import gradio as gr

# Path to the pictures folder
PICTURES_FOLDER = "pictures"
ELO_FILE = "elo_data.json"
STATS_FILE = "stats_data.json"
REAL_PASSWORD = "hb23fb823bc283ycb823fgh91l2gfj3hg1fjkhg23f.,.42.34,."
SHARE = False

# Elo rating constants
K = 32  # Base K-factor for Elo calculation

# Initialize Elo data
if not os.path.exists(ELO_FILE):
    elo_data = {}
    for image in os.listdir(PICTURES_FOLDER):
        if image.lower().endswith((".png", ".jpg", ".jpeg")):
            elo_data[image] = 1000
    with open(ELO_FILE, "w") as f:
        json.dump(elo_data, f)
else:
    with open(ELO_FILE, "r") as f:
        elo_data = json.load(f)
    # Ensure any new images are added to elo_data
    for image in os.listdir(PICTURES_FOLDER):
        if image.lower().endswith((".png", ".jpg", ".jpeg")) and image not in elo_data:
            elo_data[image] = 1000
    with open(ELO_FILE, "w") as f:
        json.dump(elo_data, f)

# Initialize stats data
if not os.path.exists(STATS_FILE):
    stats_data = {
        "total_ratings": 0,
        "images_rated": [],
        "rating_distribution": {
            "pic1_much_better": 0,
            "pic1_slightly_better": 0,
            "equal": 0,
            "pic2_slightly_better": 0,
            "pic2_much_better": 0
        },
        "comparisons_made": 0,  # New field for comparisons made
        "pairs_rated": []  # Track unique unordered pairs by index ("i-j")
    }
    with open(STATS_FILE, "w") as f:
        json.dump(stats_data, f)
else:
    with open(STATS_FILE, "r") as f:
        stats_data = json.load(f)
    if "comparisons_made" not in stats_data:
        stats_data["comparisons_made"] = 0  # Add field if missing
    if "pairs_rated" not in stats_data:
        stats_data["pairs_rated"] = []  # Initialize if missing
        with open(STATS_FILE, "w") as f:
            json.dump(stats_data, f)

# Elo calculation function
def calculate_elo(winner_elo, loser_elo, outcome):
    expected_winner = 1 / (1 + 10 ** ((loser_elo - winner_elo) / 400))
    expected_loser = 1 / (1 + 10 ** ((winner_elo - loser_elo) / 400))

    if outcome == "much_better":
        k_factor = K
    elif outcome == "slightly_better":
        k_factor = K * 0.6
    elif outcome == "equal":
        k_factor = K * 0.2

    # Winner gains points, loser loses points (zero-sum)
    winner_change = k_factor * (1 - expected_winner)
    loser_change = k_factor * (0 - expected_loser)

    return round(winner_elo + winner_change), round(loser_elo + loser_change)

# Randomly select two images
def get_random_images():
    images = os.listdir(PICTURES_FOLDER)
    images = [img for img in images if img.lower().endswith((".png", ".jpg", ".jpeg"))]  
    return random.sample(images, 2)

# Helper function to find actual filename in folder (handles extension mismatches)
def find_actual_filename(filename):
    """Find the actual file in the pictures folder, handling .jpg/.jpeg differences"""
    # First try exact match
    if os.path.exists(os.path.join(PICTURES_FOLDER, filename)):
        return filename
    
    # Try finding by base name (without extension)
    base_name = os.path.splitext(filename)[0]
    for img in os.listdir(PICTURES_FOLDER):
        if os.path.splitext(img)[0] == base_name and img.lower().endswith((".png", ".jpg", ".jpeg")):
            return img
    
    return filename  # Return original if not found

# Update Elo ratings based on user input
def update_elo(image1, image2, outcome):
    global elo_data, stats_data
    
    # Reload elo_data to get latest data
    with open(ELO_FILE, "r") as f:
        elo_data = json.load(f)
    
    # Reload stats_data
    with open(STATS_FILE, "r") as f:
        stats_data = json.load(f)

    # Extract filenames from paths and find actual filenames in folder
    image1_basename = os.path.basename(image1)
    image2_basename = os.path.basename(image2)
    
    # Find actual filenames (handles .jpg/.jpeg mismatches)
    image1 = find_actual_filename(image1_basename)
    image2 = find_actual_filename(image2_basename)
    
    # Ensure both images are in elo_data
    if image1 not in elo_data:
        elo_data[image1] = 1000
    if image2 not in elo_data:
        elo_data[image2] = 1000

    if outcome == "pic1_much_better":
        elo_data[image1], elo_data[image2] = calculate_elo(elo_data[image1], elo_data[image2], "much_better")
    elif outcome == "pic1_slightly_better":
        elo_data[image1], elo_data[image2] = calculate_elo(elo_data[image1], elo_data[image2], "slightly_better")
    elif outcome == "equal":
        elo_data[image1], elo_data[image2] = calculate_elo(elo_data[image1], elo_data[image2], "equal")
    elif outcome == "pic2_slightly_better":
        elo_data[image2], elo_data[image1] = calculate_elo(elo_data[image2], elo_data[image1], "slightly_better")
    elif outcome == "pic2_much_better":
        elo_data[image2], elo_data[image1] = calculate_elo(elo_data[image2], elo_data[image1], "much_better")

    # Save updated Elo data
    with open(ELO_FILE, "w") as f:
        json.dump(elo_data, f, indent=2)
    
    # Update stats
    stats_data["total_ratings"] += 1
    # Record unique unordered pair by stable index mapping
    images_list = sorted([img for img in os.listdir(PICTURES_FOLDER) if img.lower().endswith((".png", ".jpg", ".jpeg"))])
    index_map = {name: idx for idx, name in enumerate(images_list)}
    i1 = index_map.get(image1)
    i2 = index_map.get(image2)
    if i1 is not None and i2 is not None:
        a, b = sorted([i1, i2])
        pair_id = f"{a}-{b}"
        if pair_id not in stats_data.get("pairs_rated", []):
            stats_data.setdefault("pairs_rated", []).append(pair_id)
            stats_data["comparisons_made"] = len(stats_data["pairs_rated"])  # keep in sync
    if image1 not in stats_data["images_rated"]:
        stats_data["images_rated"].append(image1)
    if image2 not in stats_data["images_rated"]:
        stats_data["images_rated"].append(image2)
    stats_data["rating_distribution"][outcome] += 1
    
    # Save updated stats
    with open(STATS_FILE, "w") as f:
        json.dump(stats_data, f, indent=2)

    return f"Elo updated! {image1}: {elo_data[image1]}, {image2}: {elo_data[image2]}"



# Automatically load random images and refresh after rating
def load_random_images():
    img1, img2 = get_random_images()
    return os.path.join(PICTURES_FOLDER, img1), os.path.join(PICTURES_FOLDER, img2)

def update_elo_and_load_new(image1, image2, outcome):
    update_elo(image1, image2, outcome)
    return load_random_images()

# Leaderboard display with colored backgrounds for top 3
def display_leaderboard():
    global elo_data
    # Reload elo_data to get latest changes
    with open(ELO_FILE, "r") as f:
        elo_data = json.load(f)
    
    sorted_elo = sorted(elo_data.items(), key=lambda x: x[1], reverse=True)
    leaderboard_html = """
    <style>
        .leaderboard-table {
            width: 100%;
            text-align: left;
            border-collapse: collapse;
        }
        .leaderboard-table th {
            background-color: #333;
            color: white;
            padding: 12px;
            font-weight: bold;
        }
        .leaderboard-table td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        .rank-1 {
            background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        }
        .rank-2 {
            background: linear-gradient(135deg, #C0C0C0 0%, #A8A8A8 100%);
        }
        .rank-3 {
            background: linear-gradient(135deg, #CD7F32 0%, #8B4513 100%);
        }
        .rank-1 td, .rank-2 td, .rank-3 td {
            color: white;
            text-shadow: 1px 1px 2px black, -1px -1px 2px black, 1px -1px 2px black, -1px 1px 2px black;
            font-weight: bold;
        }
    </style>
    <table class='leaderboard-table'>
        <tr>
            <th>Rank</th>
            <th>Image</th>
            <th>Filename</th>
            <th>Elo</th>
        </tr>
    """
    
    for rank, (image, elo) in enumerate(sorted_elo, 1):
        image_path = os.path.join(PICTURES_FOLDER, image)
        row_class = f"rank-{rank}" if rank <= 3 else ""
        
        # Convert image to base64 for HTML display
        img_src = ""
        
        # Debug: Print information
        print(f"Processing rank {rank}: {image} (ELO: {elo})")
        #print(f"Image path: {image_path}")
        #print(f"File exists: {os.path.exists(image_path)}")
        
        if os.path.exists(image_path) and os.path.isfile(image_path):
            try:
                # Get file size to verify it's readable
                #file_size = os.path.getsize(image_path)
                #print(f"File size: {file_size} bytes")
                
                with open(image_path, "rb") as img_file:
                    img_bytes = img_file.read()
                    #print(f"Read {len(img_bytes)} bytes")
                    img_data = base64.b64encode(img_bytes).decode('utf-8')
                    #print(f"Base64 encoded length: {len(img_data)}")
                    
                    # Detect image type
                    ext = image.lower().split('.')[-1]
                    if ext in ['jpg', 'jpeg']:
                        mime_type = 'image/jpeg'
                    elif ext == 'png':
                        mime_type = 'image/png'
                    else:
                        mime_type = 'image/jpeg'
                    
                    img_src = f"data:{mime_type};base64,{img_data}"
                    #print(f"Successfully created image src for {image}")
            except Exception as e:
                print(f"ERROR loading image {image}: {type(e).__name__}: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"File not found or not a file: {image_path}")
        
        leaderboard_html += f"<tr class='{row_class}'>"
        leaderboard_html += f"<td>{rank}</td>"
        if img_src:
            leaderboard_html += f"<td><img src='{img_src}' alt='{image}' style='height:50px; object-fit:cover;'></td>"
        else:
            leaderboard_html += f"<td style='color:red;'>No image: {image}</td>"
        leaderboard_html += f"<td>{image}</td>"
        leaderboard_html += f"<td>{elo}</td>"
        leaderboard_html += "</tr>"
    
    leaderboard_html += "</table>"
    return leaderboard_html

# Stats functions
def get_stats():
    with open(STATS_FILE, "r") as f:
        stats = json.load(f)

    total_images = len([img for img in os.listdir(PICTURES_FOLDER) if img.lower().endswith((".png", ".jpg", ".jpeg"))])
    images_rated = len(stats.get("images_rated", []))

    # Unique unordered pair space and comparisons made
    total_possible_comparisons = (total_images * (total_images - 1)) // 2 if total_images >= 2 else 0
    comparisons_made = len(stats.get("pairs_rated", []))

    return (
        stats.get("total_ratings", 0),
        f"{images_rated} out of {total_images}",
        stats.get("rating_distribution", {}),
        f"{comparisons_made} out of {total_possible_comparisons}"
    )

# Ensure the DataFrame has explicit data types for Altair compatibility
def create_rating_distribution_chart():
    with open(STATS_FILE, "r") as f:
        stats = json.load(f)

    dist = stats["rating_distribution"]
    total = sum(dist.values())

    labels = ["Pic 1 Much Better", "Pic 1 Slightly Better", "Equal", "Pic 2 Slightly Better", "Pic 2 Much Better"]
    values = [
        dist["pic1_much_better"],
        dist["pic1_slightly_better"],
        dist["equal"],
        dist["pic2_slightly_better"],
        dist["pic2_much_better"]
    ]

    if total == 0:
        percentages = [0, 0, 0, 0, 0]
    else:
        percentages = [v/total*100 for v in values]

    # Return as pandas DataFrame with explicit types
    df = pd.DataFrame({
        "Rating Type": pd.Series(labels, dtype="string"),
        "Percentage (%)": pd.Series(percentages, dtype="float")
    })

    return df

def reset_elo_with_password(password):
    if password != REAL_PASSWORD:
        return "❌ Incorrect password!"
    
    # Reset ELO data
    elo_data = {}
    for image in os.listdir(PICTURES_FOLDER):
        if image.lower().endswith((".png", ".jpg", ".jpeg")):
            elo_data[image] = 1000
    
    with open(ELO_FILE, "w") as f:
        json.dump(elo_data, f, indent=2)
    
    # Reset stats
    stats_data = {
        "total_ratings": 0,
        "images_rated": [],
        "rating_distribution": {
            "pic1_much_better": 0,
            "pic1_slightly_better": 0,
            "equal": 0,
            "pic2_slightly_better": 0,
            "pic2_much_better": 0
        },
        "comparisons_made": 0,  # Reset comparisons made
        "pairs_rated": []
    }
    
    with open(STATS_FILE, "w") as f:
        json.dump(stats_data, f, indent=2)
    
    return "✅ ELO ratings and stats have been reset!"

# Custom CSS for colored buttons
custom_css = """
.red-button {
    background: linear-gradient(135deg, #ff4444 0%, #cc0000 100%) !important;
    color: white !important;
    border: none !important;
}
.light-red-button {
    background: linear-gradient(135deg, #d99 0%, #b88 100%) !important;
    color: white !important;
    border: none !important;
}
.gray-button {
    background: linear-gradient(135deg, #999 0%, #777 100%) !important;
    color: white !important;
    border: none !important;
}
.light-blue-button {
    background: linear-gradient(135deg, #99d 0%, #88b 100%) !important;
    color: white !important;
    border: none !important;
}
.blue-button {
    background: linear-gradient(135deg, #4444ff 0%, #0000cc 100%) !important;
    color: white !important;
    border: none !important;
}
"""

with gr.Blocks(css=custom_css, title="Picture Championship") as demo:
    gr.Markdown("# 🏆 Picture Championship")
    gr.Markdown("""Compare two randomly selected images and rate which one is better. 
    Each image has an ELO rating that starts at 1000 and changes based on match outcomes. 
    The more decisive the victory, the more ELO points are exchanged between the images. 
    Check the Leaderboard tab to see the rankings!""")
    
    with gr.Tab("Arena"):
        with gr.Row():
            image1 = gr.Image(type="filepath", label="Image 1", interactive=False)
            image2 = gr.Image(type="filepath", label="Image 2", interactive=False)

        with gr.Row():
            btn1 = gr.Button("Pic 1 is much better", elem_classes="red-button")
            btn2 = gr.Button("Pic 1 is slightly better", elem_classes="light-red-button")
            btn3 = gr.Button("They're equal", elem_classes="gray-button")
            btn4 = gr.Button("Pic 2 is slightly better", elem_classes="light-blue-button")
            btn5 = gr.Button("Pic 2 is much better", elem_classes="blue-button")

        # Auto-load images on page load
        demo.load(load_random_images, None, [image1, image2])

        btn1.click(lambda img1, img2: update_elo_and_load_new(img1, img2, "pic1_much_better"), [image1, image2], [image1, image2])
        btn2.click(lambda img1, img2: update_elo_and_load_new(img1, img2, "pic1_slightly_better"), [image1, image2], [image1, image2])
        btn3.click(lambda img1, img2: update_elo_and_load_new(img1, img2, "equal"), [image1, image2], [image1, image2])
        btn4.click(lambda img1, img2: update_elo_and_load_new(img1, img2, "pic2_slightly_better"), [image1, image2], [image1, image2])
        btn5.click(lambda img1, img2: update_elo_and_load_new(img1, img2, "pic2_much_better"), [image1, image2], [image1, image2])

    with gr.Tab("Leaderboard") as leaderboard_tab:
        leaderboard = gr.HTML()
        
        # Auto-refresh when tab is opened
        leaderboard_tab.select(display_leaderboard, None, leaderboard)
    
    with gr.Tab("Stats and Settings") as stats_tab:
        gr.Markdown("## 📊 Statistics")
        
        with gr.Row():
            with gr.Column():
                total_ratings_display = gr.Textbox(label="Total Ratings Made", interactive=False)
                images_rated_display = gr.Textbox(label="Images Rated", interactive=False)
            with gr.Column():
                comparisons_display = gr.Textbox(label="Comparisons Made (unique pairs)", interactive=False)
                elo_range_display = gr.Textbox(label="ELO Range (Min - Max)", interactive=False)
        
        gr.Markdown("### Rating Distribution")
        rating_dist_chart = gr.BarPlot(
            value=pd.DataFrame({
                "Rating Type": pd.Series([], dtype="string"),
                "Percentage (%)": pd.Series([], dtype="float"),
            }),
            x="Rating Type",
            y="Percentage (%)",
            title="Distribution of Ratings Given",
            vertical=True,
            width=600,
            height=400
        )
        
        refresh_stats_btn = gr.Button("🔄 Refresh Stats")
        
        gr.Markdown("---")
        gr.Markdown("## ⚙️ Settings")
        
        with gr.Row():
            password_input = gr.Textbox(label="Password", type="password", placeholder="Enter password to reset")
            reset_button = gr.Button("🔄 Reset ELO Leaderboards", variant="stop")
        
        reset_message = gr.Textbox(label="Status", interactive=False)
        
        # Update the update_stats function to include comparisons made and remove average ELO
        def update_stats():
            total_ratings, images_rated, dist, comparisons = get_stats()
            chart_data = create_rating_distribution_chart()

            # Calculate range stats
            with open(ELO_FILE, "r") as f:
                elo_data_local = json.load(f)
            elos = list(elo_data_local.values())
            min_elo = min(elos) if elos else 1000
            max_elo = max(elos) if elos else 1000

            return (
                str(total_ratings),
                images_rated,
                comparisons,
                f"{min_elo} - {max_elo}",
                chart_data
            )
        
        # Auto-refresh stats when tab is opened
        stats_tab.select(
            update_stats,
            None,
            [total_ratings_display, images_rated_display, comparisons_display, elo_range_display, rating_dist_chart]
        )
        
        refresh_stats_btn.click(
            update_stats,
            None,
            [total_ratings_display, images_rated_display, comparisons_display, elo_range_display, rating_dist_chart]
        )
        
        reset_button.click(reset_elo_with_password, password_input, reset_message)

demo.launch(share=SHARE)