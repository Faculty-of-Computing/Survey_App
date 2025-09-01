import cloudinary.uploader

def upload_to_cloudinary(file, folder="uploads"):
    """
    Upload a file to Cloudinary and return its secure URL.
    :param file: FileStorage object (from request.files['file'])
    :param folder: Folder name in your Cloudinary dashboard
    :return: URL string or None if failed
    """
    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="auto"  # auto detects images, pdfs, videos etc.
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"Cloudinary upload failed: {e}")
        return None
