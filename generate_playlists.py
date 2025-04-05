import requests
import gzip
import json
import os
import logging
from io import BytesIO

# --- Configuration ---
OUTPUT_DIR = "playlists"
USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
REQUEST_TIMEOUT = 30 # seconds

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Helper Functions ---
def fetch_url(url, is_json=True, is_gzipped=False, headers=None, stream=False):
    """Fetches data from a URL, handles gzip, and parses JSON if needed."""
    logging.info(f"Fetching URL: {url}")
    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT, stream=stream)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)

        if stream: # Return the raw response object for streaming content (like Tubi's M3U)
             logging.info("Returning streaming response.")
             return response

        content = response.content
        if is_gzipped:
            logging.info("Decompressing gzipped content.")
            try:
                # Use BytesIO to treat the byte string as a file-like object
                with gzip.GzipFile(fileobj=BytesIO(content), mode='rb') as f:
                    content = f.read()
                content = content.decode('utf-8') # Decode bytes to string
            except gzip.BadGzipFile:
                logging.warning("Content was not gzipped, trying as plain text.")
                content = content.decode('utf-8') # Assume it was plain text
            except Exception as e:
                 logging.error(f"Error decompressing gzip: {e}")
                 raise # Re-raise the exception

        else:
             content = content.decode('utf-8') # Decode bytes to string for non-gzipped

        if is_json:
            logging.info("Parsing JSON data.")
            return json.loads(content)
        else:
            logging.info("Returning raw text content.")
            return content # Return raw text if not JSON

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching {url}: {e}")
        return None
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from {url}: {e}")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred for {url}: {e}")
        return None

def write_m3u_file(filename, content):
    """Writes content to a file in the output directory."""
    if not os.path.exists(OUTPUT_DIR):
        logging.info(f"Creating output directory: {OUTPUT_DIR}")
        os.makedirs(OUTPUT_DIR)

    filepath = os.path.join(OUTPUT_DIR, filename)
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        logging.info(f"Successfully wrote playlist to {filepath}")
    except IOError as e:
        logging.error(f"Error writing file {filepath}: {e}")

def format_extinf(channel_id, tvg_id, tvg_chno, tvg_name, tvg_logo, group_title, display_name):
    """Formats the #EXTINF line."""
    # Ensure tvg_chno is empty if None or invalid
    chno_str = str(tvg_chno) if tvg_chno is not None and str(tvg_chno).isdigit() else ""
    
    # Basic sanitization for names/titles within the M3U format
    sanitized_tvg_name = tvg_name.replace('"', "'")
    sanitized_group_title = group_title.replace('"', "'")
    sanitized_display_name = display_name.replace(',', '') # Commas break the EXTINF line itself

    return (f'#EXTINF:-1 '
            f'channel-id="{channel_id}" '
            f'tvg-id="{tvg_id}" '
            f'tvg-chno="{chno_str}" '
            f'tvg-name="{sanitized_tvg_name}" '
            f'tvg-logo="{tvg_logo}" '
            f'group-title="{sanitized_group_title}",'
            f'{sanitized_display_name}\n')

# --- Service Functions ---
def generate_stirr_m3u(sort='name'):
    """Generates M3U playlist for Stirr."""
    STIRR_URL = 'https://github.com/matthuisman/i.mjh.nz/raw/refs/heads/master/Stirr/.channels.json.gz'
    STREAM_URL_TEMPLATE = 'https://jmp2.uk/str-{id}.m3u8'
    EPG_URL = 'https://github.com/matthuisman/i.mjh.nz/raw/master/Stirr/all.xml.gz' # Note: master branch, not refs/heads/master for EPG usually

    logging.info("--- Generating Stirr playlist ---")
    data = fetch_url(STIRR_URL, is_json=True, is_gzipped=True)
    if not data or 'channels' not in data:
        logging.error("Failed to fetch or parse Stirr data.")
        return

    output_lines = [f'#EXTM3U url-tvg="{EPG_URL}"\n']
    channels_to_process = data.get('channels', {})

    # Sort channels
    try:
        if sort == 'chno':
             sorted_channel_ids = sorted(channels_to_process.keys(), key=lambda k: int(channels_to_process[k].get('chno', 99999)))
        else: # Default to name sort
             sorted_channel_ids = sorted(channels_to_process.keys(), key=lambda k: channels_to_process[k].get('name', '').lower())
    except Exception as e:
        logging.warning(f"Sorting failed for Stirr, using default order. Error: {e}")
        sorted_channel_ids = list(channels_to_process.keys())

    # Build M3U entries
    for channel_id in sorted_channel_ids:
        channel = channels_to_process[channel_id]
        chno = channel.get('chno')
        name = channel.get('name', 'Unknown Channel')
        logo = channel.get('logo', '')
        groups_list = channel.get('groups', [])
        group_title = ', '.join(groups_list) if groups_list else 'Uncategorized'
        tvg_id = channel_id # Stirr IDs seem unique enough

        extinf = format_extinf(channel_id, tvg_id, chno, name, logo, group_title, name)
        stream_url = STREAM_URL_TEMPLATE.replace('{id}', channel_id)
        output_lines.append(extinf)
        output_lines.append(stream_url + '\n')

    write_m3u_file("stirr_all.m3u", "".join(output_lines))

# --- Main Execution ---
if __name__ == "__main__":
    logging.info("Starting playlist generation process...")

    generate_stirr_m3u(sort='name')

    logging.info("Playlist generation process finished.")
