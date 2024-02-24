from PIL import Image
from io import BytesIO
import os
import boto3
import environ
import time
import base64


def save_image(image_str, type, user, receiver=None):
    """
    This function takes in a base64 encoded image string and saves it to the CDN.
    """
    image_data = base64.b64decode(image_str)
    image = Image.open(BytesIO(image_data))

    # Convert back to base64 with smaller size
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=30)

    # Convert back to bytes
    image_byte = buffer.getvalue()

    # Create a unique filename based on the current time and the user's username:
    filename = f"{int(time.time())}_{user.username}.jpg"

    # Define the path to the file
    if type == 'thumbnail':
        path = f"media/user/{user.username}/profile_picture/{filename}"
    elif type == 'message':
        path = f"media/user/{user.username}/messages/{receiver.username}/{filename}"

    return upload_to_cdn(image_byte, path)


def upload_to_cdn(image, path):
    env = environ.Env()
    environ.Env.read_env()

    session = boto3.Session(
        aws_access_key_id=os.getenv(
            'CDN_ACCESS_KEY', env('CDN_ACCESS_KEY')),
        aws_secret_access_key=os.getenv(
            'CDN_SECRET_ACCESS_KEY', env('CDN_SECRET_ACCESS_KEY')),
        region_name='sgp1'
    )

    client = session.client('s3',
                            endpoint_url='https://sgp1.digitaloceanspaces.com',
                            config=boto3.session.Config(
                                signature_version='s3v4'),
                            region_name='sgp1',
                            aws_access_key_id=os.getenv(
                                'CDN_ACCESS_KEY', env('CDN_ACCESS_KEY')),
                            aws_secret_access_key=os.getenv(
                                'CDN_SECRET_ACCESS_KEY', env('CDN_SECRET_ACCESS_KEY')),
                            )

    client.put_object(Bucket='tahcemitlaer', Key=path,
                      Body=image, ACL='public-read')

    image_cdn_url = "https://tahcemitlaer.sgp1.cdn.digitaloceanspaces.com/" + path

    return image_cdn_url
