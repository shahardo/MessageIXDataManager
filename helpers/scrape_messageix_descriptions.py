import requests
from bs4 import BeautifulSoup
import yaml
import csv
import sys
import os

def scrape_message_descriptions(url):
    """
    Scrape technologies and relations from the MESSAGEix documentation page.

    Args:
        url (str): URL of the page to scrape

    Returns:
        list: List of dictionaries with relation data
    """
    try:
        # Fetch the page
        response = requests.get(url)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all YAML code blocks
        yaml_blocks = soup.find_all('div', class_='highlight-yaml')

        relations_dict = {}

        for block in yaml_blocks:
            pre_tag = block.find('pre')
            if pre_tag:
                yaml_text = pre_tag.get_text()
                try:
                    # Parse YAML
                    data = yaml.safe_load(yaml_text)

                    # Process the data
                    if isinstance(data, dict):
                        # List A and CD-LINKS format
                        for relation_name, details in data.items():
                            if isinstance(details, dict):
                                relation_info = {
                                    'technology': relation_name,
                                    'group': details.get('group', ''),
                                    'parameters': details.get('parameters', ''),
                                    'description': details.get('description', '').strip() if details.get('description') else '',
                                    'technology-entry': details.get('technology-entry', ''),
                                }
                                # Merge with existing entry if present
                                if relation_name in relations_dict:
                                    existing = relations_dict[relation_name]
                                    for key, value in relation_info.items():
                                        if key != 'technology' and (not existing.get(key) or existing.get(key) == ''):
                                            existing[key] = value
                                        elif key == 'description' and value and existing.get(key) != value:
                                            # If descriptions differ, keep the longer one
                                            if len(value) > len(existing.get(key, '')):
                                                existing[key] = value
                                else:
                                    relations_dict[relation_name] = relation_info
                    elif isinstance(data, list):
                        # List B format - just names, no details
                        for relation_name in data:
                            if isinstance(relation_name, str):
                                relation_info = {
                                    'technology': relation_name,
                                    'group': '',
                                    'parameters': '',
                                    'description': '',
                                    'technology-entry': '',
                                }
                                # Only add if not already present with more info
                                if relation_name not in relations_dict:
                                    relations_dict[relation_name] = relation_info

                except yaml.YAMLError as e:
                    print(f"Error parsing YAML block: {e}", file=sys.stderr)
                    continue

        return list(relations_dict.values())

    except requests.RequestException as e:
        print(f"Error fetching URL: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error during scraping: {e}", file=sys.stderr)
        return []

def export_to_csv(data, output_file):
    """
    Export the scraped data to a CSV file.

    Args:
        data (list): List of dictionaries with relation data
        output_file (str): Path to output CSV file
    """
    if not data:
        print("No data to export", file=sys.stderr)
        return

    # Define the desired column order: technology first, description last
    desired_order = ['technology', 'group', 'parameters', 'technology-entry', 'description']

    # Get all possible keys
    all_keys = set()
    for item in data:
        all_keys.update(item.keys())

    # Use desired order for known columns, then add any additional columns
    fieldnames = [key for key in desired_order if key in all_keys]
    fieldnames += sorted([key for key in all_keys if key not in desired_order])

    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)

        print(f"Data exported to {output_file}")

    except IOError as e:
        print(f"Error writing to CSV file: {e}", file=sys.stderr)

def main():
    urls = [
        "https://docs.messageix.org/projects/models/en/latest/pkg-data/relation.html",
        "https://docs.messageix.org/projects/models/en/latest/pkg-data/codelists.html"
    ]
    output_file = "./helpers/message_relations.csv"

    print("Scraping MESSAGEix data...")
    all_data = []
    for url in urls:
        data = scrape_message_descriptions(url)
        all_data.extend(data)

    if all_data:
        print(f"Found {len(all_data)} entries")
        export_to_csv(all_data, output_file)
        print(f"Export completed. File saved as {output_file}")
    else:
        print("No data found")
        sys.exit(1)

if __name__ == "__main__":
    main()
