import discord
import asyncio
import time

# -----------------------------
# CONFIG
# -----------------------------
TOKEN = ""  # replace with your bot token
CHANNEL_ID =   # replace with your target channel ID
LINKS_FILE = "downloaded_links.txt"
BATCH_SIZE = 20  # number of images to send concurrently
MAX_RETRIES = 5  # max retries per message

# -----------------------------
# DISCORD CLIENT SETUP
# -----------------------------
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# -----------------------------
# ON READY
# -----------------------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        print("❌ Channel not found")
        await client.close()
        return

    # -------------------------
    # LOAD LINKS & REMOVE DUPES
    # -------------------------
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        raw_links = [line.strip() for line in f if line.strip()]

    # Convert to set to remove duplicates
    unique_links = list(dict.fromkeys(raw_links))

    print(f"[*] Loaded {len(raw_links)} links.")
    print(f"[*] Unique filtered links: {len(unique_links)}")
    print(f"[*] Sending embeds...\n")

    # -------------------------
    # SEND SINGLE EMBED
    # -------------------------
    async def send_embed(url):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                embed = discord.Embed()
                embed.set_image(url=url)
                await channel.send(embed=embed)

                print(f"[+] Sent: {url}")
                return True

            except discord.errors.HTTPException as e:
                if e.status == 429:
                    retry_after = getattr(e, "retry_after", 2)
                    print(f"[!] Rate limited on {url}. Retrying in {retry_after}s")
                    await asyncio.sleep(retry_after)
                    retries += 1
                else:
                    print(f"[!] Failed to send {url}: {e}")
                    return False

        print(f"[!] Max retries reached for {url}")
        return False

    # -------------------------
    # SEND IN BATCHES
    # -------------------------
    for i in range(0, len(unique_links), BATCH_SIZE):
        batch = unique_links[i:i + BATCH_SIZE]
        await asyncio.gather(*(send_embed(url) for url in batch))
        await asyncio.sleep(1)

    print("[*] Finished sending all embeds.")
    await client.close()

# -----------------------------
# RUN BOT
# -----------------------------
client.run(TOKEN)
