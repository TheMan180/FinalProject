import requests
from creds import get_creds
iam_token, folder_id = get_creds()

def speech_to_text(data):
    iam_token = '<iam_token>'
    folder_id = '<folder_id>'

    params = "&".join([
        "topic=general",
        f"folderId={folder_id}",
        "lang=ru-RU"
    ])

    headers = {
        'Authorization': f'Bearer {iam_token}',
    }

    response = requests.post(
            f"https://stt.api.cloud.yandex.net/speech/v1/stt:recognize?{params}",
        headers=headers,
        data=data
    )

    decoded_data = response.json()
    if decoded_data.get("error_code") is None:
        return True, decoded_data.get("result")
    else:
        return False, "При запросе в SpeechKit возникла ошибка"
if __name__ == "__main__":
    audio_file_path = "путь/к/твоему/аудиофайлу.ogg"

    with open(audio_file_path, "rb") as audio_file:
        audio_data = audio_file.read()

    success, result = speech_to_text(audio_data)

    if success:
        print("Распознанный текст: ", result)
    else:
        print("Ошибка при распознавании речи: ", result)
    audio_file_path = "grisha.ogg"
def text_to_speech(text):
    iam_token = '<iam_token>'
    folder_id = '<folder_id>'
    headers = {
        'Authorization': f'Bearer {iam_token}',
    }
    data = {
        'text': text,
        'lang': 'ru-RU',
        'voice': 'filipp',
        'folderId': folder_id,
    }

    response = requests.post(
        'https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize',
        headers=headers,
        data=data
    )
    if response.status_code == 200:
        return True, response.content
    else:
        return False, "При запросе в SpeechKit возникла ошибка"
if __name__ == "__main__":
        text = "Привет! Я учусь работать с API SpeechKit. Это очень интересно!"
        success, response = text_to_speech(text)
        if success:
            with open("output.ogg", "wb") as audio_file:
                audio_file.write(response)
            print("Аудиофайл успешно сохранен как output.ogg")
        else:
            print("Ошибка:", response)
