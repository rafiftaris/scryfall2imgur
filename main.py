import argparse
import csv
import requests
import time
import os
import os.path as path

CARD_NAME_COLUMN_PATH="CardName"
SET_CODE_COLUMN_PATH="SetCode"
IMAGE_PATH_COLUMN_NAME="ImagePath"
ERROR_COLUMN_PATH="ErrorMessage"
IMGUR_URI_COLUMN_PATH="ImgurUri"

def get_card_image_url(card_name, set_code):
    base_url = 'https://api.scryfall.com/cards/named'
    params = {
        'fuzzy': card_name,
        'set': set_code
    }
    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        card_data = response.json()
        if 'image_uris' not in card_data.keys():
            if 'image_uris' in card_data['card_faces'][0].keys():
                return card_data['card_faces'][0]['image_uris']['normal']
            else:
                raise Exception("Image uris not found")
        return card_data['image_uris']['normal']  # This gets the normal image URL
    else:
        raise Exception(f"Error fetching {card_name} ({set_code}): {response.status_code}")


def process_csv_and_download_images(input_file, output_dir):
    csv_file_input = open(input_file, 'r')
    reader = csv.DictReader(csv_file_input)
    
    file_name = path.basename(input_file)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    csv_file_output = open(path.join(output_dir,file_name),"w")
    csv_file_output.write(f"{CARD_NAME_COLUMN_PATH},{SET_CODE_COLUMN_PATH},{IMAGE_PATH_COLUMN_NAME}\n")
    csv_file_errors = open(path.join(output_dir,"errors.csv"),"w")
    csv_file_errors.write(f"{CARD_NAME_COLUMN_PATH},{SET_CODE_COLUMN_PATH},{ERROR_COLUMN_PATH}\n")

    if not os.path.exists('card_images'):
        os.makedirs('card_images')

    counter = 0
    for row in reader:
        counter += 1
        if counter % 10 == 0:
            time.sleep(1)

        card_name = row['Card Name']  # TODO: replace card name with pipe
        set_code = row['Set Code']    # Adjust column name as per your CSV
        image_url = ""
        try:
            image_url = get_card_image_url(card_name, set_code)
        except Exception as e:
            print(f"Failed to fetch {card_name} ({set_code}): {str(e)}")
            csv_file_errors.write(f"{card_name},{set_code},{str(e)}\n")
            continue
        
        # Download the image
        image_response = requests.get(image_url)
        if image_response.status_code == 200:
            image_path = os.path.join('card_images', f"{card_name.replace("/",";")}_{set_code}.jpg")
            with open(image_path, 'wb') as img_file:
                img_file.write(image_response.content)
            print(f"Downloaded {card_name} ({set_code})")
            csv_file_output.write(f"{card_name},{set_code},{image_path}\n")

    csv_file_input.close()
    csv_file_output.close()
    csv_file_errors.close()


def upload_image_to_imgur(image_path, client_id):
    url = "https://api.imgur.com/3/image"
    headers = {
        "Authorization": f"Client-ID {client_id}"
    }
    with open(image_path, "rb") as image_file:
        payload = {"image": image_file.read()}
        response = requests.post(url, headers=headers, files=payload)

    if response.status_code == 200:
        data = response.json()
        link = data["data"]["link"]
        return link
    else:
        print(f"Failed to upload image: {response.status_code}")
        raise Exception(f"Failed to upload image. Response: {response.json()}")
    
def process_csv_and_upload_images(input_file,output_dir,client_id):
    csv_file_input = open(input_file, 'r')
    reader = csv.DictReader(csv_file_input)

    file_name_without_extension, _ = path.splitext(path.basename(input_file))
    csv_file_output = open(path.join(output_dir, file_name_without_extension + "_imgur.csv"), 'w')
    csv_file_output.write(f"{CARD_NAME_COLUMN_PATH},{SET_CODE_COLUMN_PATH},{IMGUR_URI_COLUMN_PATH}\n")
    csv_file_errors = open(path.join(output_dir,"errors_imgur.csv"),"w")
    csv_file_errors.write(f"{CARD_NAME_COLUMN_PATH},{SET_CODE_COLUMN_PATH},{ERROR_COLUMN_PATH}\n")

    counter = 0
    for row in reader:
        counter += 1
        if counter % 10 == 0:
            time.sleep(1)
        try:
            imgur_link = upload_image_to_imgur(row[IMAGE_PATH_COLUMN_NAME],client_id)
            csv_file_output.write(f"{row[CARD_NAME_COLUMN_PATH]},{row[SET_CODE_COLUMN_PATH]},{imgur_link}\n")
            print(f"Image {row[CARD_NAME_COLUMN_PATH]} ({row[SET_CODE_COLUMN_PATH]}) uploaded successfully! Link: {imgur_link}")
        except Exception as e:
            csv_file_errors.write(f"{row[CARD_NAME_COLUMN_PATH]},{row[SET_CODE_COLUMN_PATH]},{str(e)}\n")
            print(f"Failed to upload {row[CARD_NAME_COLUMN_PATH]} ({row[SET_CODE_COLUMN_PATH]}) image: {str(e)}")

    csv_file_input.close()
    csv_file_output.close()
    csv_file_errors.close()




def main():
    parser = argparse.ArgumentParser(description="Python script for batch scraping MTG singles images and upload to imgur")
    
    # Adding arguments
    parser.add_argument("-i", "--input-file", type=str, help="Path to csv file that contains 2 columns: card name and set", default="input/example.csv")
    parser.add_argument("-o", "--output-dir", type=str, help="Path to result csv folder that result file and errors file", default="output/")
    parser.add_argument("-u", "--client-id", type=str, help="Imgur Client ID", default="")
    parser.add_argument("-f", "--fixup", action="store_true", help="Fixup upload error to imgur. Only upload error files")

    # Parse arguments
    args = parser.parse_args()

    # Process the input arguments
    if args.fixup:
        # TODO: filter error and successful result and only process error result
        # TODO: replace | with , 
        pass
    else:
        # process_csv_and_download_images(args.input_file, args.output_dir)
        process_csv_and_upload_images(path.join(args.output_dir,path.basename(args.input_file)),args.output_dir,args.client_id)
        
    print("Card images uploaded to imgur. Links are stored in the csv")

if __name__ == "__main__":
    main()