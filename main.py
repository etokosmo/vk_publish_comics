import os
from dataclasses import dataclass
from random import randint
from urllib.parse import urlsplit, unquote_plus

import requests
from environs import Env

VK_API_VERSION = 5.131


@dataclass
class Comics:
    """Информация о комиксе"""
    title: str
    img_url: str
    alt_text: str
    filename: str = ""


def download_file(file_url: str, path_to_download: str = '.') -> None:
    """Скачиваем <img_url> в <path>

    Args:
        file_url (str): Ссылка на файл, который скачиваем.
        path_to_download (str): Путь куда скачивать.

    Returns:
        None.

    """
    response = requests.get(file_url)
    response.raise_for_status()

    with open(path_to_download, 'wb') as file:
        file.write(response.content)


def get_file_extension(url: str) -> str:
    """Получаем расширение файла по URL

    Args:
        url (str): URL файла.

    Returns:
        file_extension (str): расширение файла.

    """
    truncated_url = unquote_plus(
        urlsplit(url, scheme='', allow_fragments=True).path)
    filename, file_extension = os.path.splitext(truncated_url)
    return file_extension


def get_comics(comics_number: int) -> Comics:
    """Загрузка комикса с сайта xkcd.com.

    Args:
        comics_number (int): номер комикса.

    Returns:
        Comics: данные о комиксе.

    """
    url = f"https://xkcd.com/{comics_number}/info.0.json"
    response = requests.get(url)
    response.raise_for_status()
    decode_response = response.json()

    comics = Comics(
        decode_response.get("title"),
        decode_response.get("img"),
        decode_response.get("alt"),
    )
    file_extension = get_file_extension(comics.img_url)
    comics.filename = f"comics{comics_number}_{comics.title}{file_extension}"
    download_file(comics.img_url, comics.filename)
    return comics


def get_wall_upload_server(vk_app_client_id: str, vk_access_token: str) -> str:
    """Возвращает адрес сервера для загрузки фотографии на стену сообщества

    Args:
        vk_app_client_id (dict): идентификатор приложения сообщества.
        vk_access_token (str): ключ доступа VK.

    Returns:
        media_on_server_url (str): адрес сервера.

    """
    url = "https://api.vk.com/method/photos.getWallUploadServer"
    payload = {
        "group_id": vk_app_client_id,
        "access_token": vk_access_token,
        "v": VK_API_VERSION
    }
    response = requests.get(url, params=payload)
    response.raise_for_status()
    media_on_server_url = response.json().get("response").get("upload_url")
    return media_on_server_url


def upload_image(media_address: str, filename: str) -> dict:
    """Загружаем на сервер Вконтакте фото.

    Args:
        media_address (str): адрес сервера с загруженным фото.
        filename (str): имя файла с фото.

    Returns:
        Функция возвращает в ответе словарь с полями server, photo, hash.

    """
    with open(filename, 'rb') as file:
        files = {
            'photo': file,
        }
        response = requests.post(media_address, files=files)
        response.raise_for_status()
        return response.json()


def save_wall_photo(
        uploaded_media: dict,
        vk_app_client_id: int,
        vk_access_token: str) -> (int, int):
    """Сохраняет фотографии после успешной загрузки на URI.

    Args:
        uploaded_media (dict): словарь с полями server, photo, hash.
        vk_app_client_id (dict): идентификатор приложения сообщества.
        vk_access_token (str): ключ доступа VK.

    Returns:
        uploaded_media_id (int): идентификатор медиа-приложения.
        app_owner_id (int): идентификатор владельца медиа-приложения.

    """
    url = "https://api.vk.com/method/photos.saveWallPhoto"
    payload = {
        "group_id": vk_app_client_id,
        "photo": uploaded_media.get("photo"),
        "server": uploaded_media.get("server"),
        "hash": uploaded_media.get("hash"),
        "access_token": vk_access_token,
        "v": VK_API_VERSION
    }
    response = requests.post(url, params=payload)
    response.raise_for_status()
    decode_response = response.json()
    uploaded_media_id = decode_response.get("response")[0].get("id")
    app_owner_id = decode_response.get("response")[0].get("owner_id")
    return uploaded_media_id, app_owner_id


def publish_wall_post(
        group_id: int,
        message: str,
        uploaded_media_id: int,
        app_owner_id: int,
        vk_access_token: str,
        from_group: int = 0) -> None:
    """Опубликовываем запись на стене группы Вконтакте.

    Args:
        group_id (int): идентификатор сообщества, где опубликуется запись.
        message (str): текст сообщения.
        uploaded_media_id (int): идентификатор медиа-приложения.
        app_owner_id (int): идентификатор владельца медиа-приложения.
        vk_access_token (str): ключ доступа VK.
        from_group (int): публикация от лица сообщества.

    Returns:
        None

    """
    url = "https://api.vk.com/method/wall.post"
    payload = {
        "owner_id": f"-{group_id}",
        "from_group": from_group,
        "message": message,
        "attachments": f"photo{app_owner_id}_{uploaded_media_id}",
        "access_token": vk_access_token,
        "v": VK_API_VERSION
    }
    response = requests.post(url, params=payload)
    response.raise_for_status()


def get_amount_comics() -> int:
    """Получаем id последнего комикса (общее количество комиксов)"""
    url = "https://xkcd.com/info.0.json"
    response = requests.get(url)
    response.raise_for_status()
    return response.json().get("num")


def delete_image(path_to_image: str) -> None:
    """Удаляем изображение с компьютера"""
    if os.path.isfile(path_to_image):
        os.remove(path_to_image)


def main():
    env = Env()
    env.read_env()
    vk_app_client_id = env.int("VK_APP_CLIENT_ID")
    vk_access_token = env("ACCESS_TOKEN")
    group_id = env.int("VK_GROUP_ID")
    from_group = env.int("FROM_GROUP", 1)

    comics_number = randint(1, get_amount_comics())
    comic = get_comics(comics_number)

    media_address = get_wall_upload_server(vk_app_client_id, vk_access_token)
    media = upload_image(media_address, comic.filename)
    media_id, owner_id = save_wall_photo(
        media,
        vk_app_client_id,
        vk_access_token
    )
    publish_wall_post(
        group_id,
        comic.alt_text,
        media_id,
        owner_id,
        vk_access_token,
        from_group
    )

    delete_image(comic.filename)


if __name__ == "__main__":
    main()