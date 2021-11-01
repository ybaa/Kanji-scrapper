import json
import urllib.request
import requests
from bs4 import BeautifulSoup
import argparse
import re

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

    for i, note in enumerate(notes):
        if note['fields']['audio']['value'] == '':
            word = note['fields']['word']['value']
            kana = ''.join(re.findall('\[(.*?)\]', note['fields']['word with furigana']['value']))
            kana_ending = re.findall('\](?:.(?!\]))+$', note['fields']['word with furigana']['value'])   # fill hiragana after kanji
            if len(kana_ending) > 0:
                kana += kana_ending[0][1:]
            
            audio_name = 'audio_%s_%s.mp3' % (kana, word)

            audio_url = 'http://assets.languagepod101.com/dictionary/japanese/audiomp3.php?kana=%s&kanji=%s' % (kana, word) 
                
            post_note_fields = dict()
            for key, val in note['fields'].items():
                post_note_fields[key] = val['value']

            try:
                invoke('storeMediaFile', filename=audio_name, url=audio_url)
                post_note_fields['audio'] = '[sound:%s]' % audio_name
                note['id'] = note.pop('noteId')
                note['fields'] = post_note_fields
                invoke('updateNoteFields', note=note)
                cards_affected += 1
                print('Updated audio for %s | %d / %d' % (word, i, len(notes)))
            except Exception as e:
                print('Cannot get audio for %s becasue of:' %word, e)
            
    print('Updated %d cards' % cards_affected)

if __name__ == '__main__':
    main()