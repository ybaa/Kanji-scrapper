import json
import urllib.request
import requests
from bs4 import BeautifulSoup
import argparse

def request(action, **params):
    return {'action': action, 'params': params, 'version': 6}

def invoke(action, **params):
    requestJson = json.dumps(request(action, **params)).encode('utf-8')
    response = json.load(urllib.request.urlopen(urllib.request.Request('http://localhost:8765', requestJson)))
    if len(response) != 2:
        raise Exception('response has an unexpected number of fields')
    if 'error' not in response:
        raise Exception('response is missing required error field')
    if 'result' not in response:
        raise Exception('response is missing required result field')
    if response['error'] is not None:
        raise Exception(response['error'])
    return response['result']

def main():
    parser = argparse.ArgumentParser(description='Update vocabulary anki deck with kanji')
    parser.add_argument('-d','--deck', help='Deck name', required=True)
    args = vars(parser.parse_args())

    deck_name = args['deck']

    notesIds = invoke('findNotes', query='deck:%s' % deck_name)
    notes = invoke('notesInfo', notes=notesIds)

    print('found %d cards in %s deck' % (len(notes), deck_name))

    cards_affected = 0

    for note in notes:
        kanji = note['fields']['Kanji']['value']
        if kanji == '':
            word = note['fields']['Front']['value']
            
            page = requests.get('https://jisho.org/search/%s' % word)
            soup = BeautifulSoup(page.content, "html.parser")
            found_kanji = soup.find_all("span", class_="character literal japanese_gothic")
            meanings = soup.find_all("div", class_="meanings english sense")
            on_readings = soup.find_all("div", class_="on readings")
            kun_readings = soup.find_all("div", class_="kun readings")

            kanji_field_content = ''

            for (i, fk), meaning in zip(enumerate(found_kanji), meanings):
                
                this_kanji = fk.text
                this_meaning = meaning.text
                
                on_reading = on_readings[i].text if i < len(on_readings) else 'On: '
                kun_reading = kun_readings[i].text if i < len(kun_readings) else 'Kun: '

                kanji_field_content += this_kanji + "<br>" + this_meaning + "<br>" + on_reading + "<br>" + kun_reading + "<br><hr>"

            if kanji_field_content == '':   # to not check kana words every time
                kanji_field_content = ' '   

            note['fields']['Kanji']['value'] = kanji_field_content
            
            post_note_fields = dict()
            for key, val in note['fields'].items():
                post_note_fields[key] = val['value']
                
            note['id'] = note.pop('noteId')
            note['fields'] = post_note_fields
            invoke('updateNoteFields', note=note)
            cards_affected += 1
            print('Updated kanji for %s' % word)
            
    print('Updated %d cards' % cards_affected)

if __name__ == '__main__':
    main()