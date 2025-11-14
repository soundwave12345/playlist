#!/usr/bin/env python3
"""
Script per creare playlist M3U da file CSV con fuzzy matching
"""

import os
import csv
from pathlib import Path
from mutagen.easyid3 import EasyID3
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from fuzzywuzzy import fuzz
import argparse


def get_audio_metadata(file_path):
    """Estrae titolo e artista dai metadati del file audio"""
    try:
        ext = file_path.suffix.lower()

        if ext == '.mp3':
            audio = EasyID3(file_path)
        elif ext == '.flac':
            audio = FLAC(file_path)
        else:
            return None, None

        title = audio.get('title', [None])[0]
        artist = audio.get('artist', [None])[0]

        return title, artist
    except Exception as e:
        print(f"Errore lettura metadati {file_path.name}: {e}")
        return None, None


def normalize_string(s):
    """Normalizza una stringa per il confronto"""
    if s is None:
        return ""
    return s.lower().strip()


def fuzzy_match_score(track_title, track_artist, file_title, file_artist):
    """Calcola uno score di matching tra traccia CSV e file audio"""
    # Score per il titolo (peso maggiore)
    title_score = fuzz.ratio(normalize_string(track_title), normalize_string(file_title))

    # Score per l'artista
    artist_score = fuzz.ratio(normalize_string(track_artist), normalize_string(file_artist))

    # Media ponderata: titolo 60%, artista 40%
    combined_score = (title_score * 0.8) + (artist_score * 0.2)

    return combined_score


def scan_audio_files(directory):
    """Scansiona la directory per file audio e ne estrae i metadati"""
    audio_files = []
    directory = Path(directory)

    for file_path in directory.rglob('*'):
        if file_path.suffix.lower() in ['.mp3', '.flac']:
            title, artist = get_audio_metadata(file_path)
            audio_files.append({
                'path': file_path,
                'title': title,
                'artist': artist
            })

    print(f"Trovati {len(audio_files)} file audio")
    return audio_files


def read_csv_tracks(csv_path):
    """Legge le tracce dal file CSV"""
    tracks = []

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2:
                title = row[0].strip()
                artist = row[1].strip()
                tracks.append({
                    'title': title,
                    'artist': artist,
                    'row': ','.join(row)
                })

    print(f"Lette {len(tracks)} tracce dal CSV")
    return tracks


def match_tracks(csv_tracks, audio_files, threshold=70):
    """Effettua il matching tra tracce CSV e file audio"""
    matched = []
    unmatched = []
    used_files = set()

    for csv_track in csv_tracks:
        best_match = None
        best_score = 0
        best_file = None

        for audio_file in audio_files:
            if audio_file['path'] in used_files:
                continue

            score = fuzzy_match_score(
                csv_track['title'],
                csv_track['artist'],
                audio_file['title'],
                audio_file['artist']
            )

            if score > best_score:
                best_score = score
                best_match = audio_file
                best_file = audio_file

        if best_score >= threshold and best_match:
            matched.append({
                'csv_track': csv_track,
                'audio_file': best_match,
                'score': best_score
            })
            used_files.add(best_match['path'])
        else:
            unmatched.append({
                'csv_track': csv_track,
                'best_match': best_file,
                'best_score': best_score
            })

    return matched, unmatched


def create_m3u_playlist(matched_tracks, output_path, audio_directory):
    """Crea il file playlist M3U"""
    audio_dir = Path(audio_directory)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("#EXTM3U")

        for match in matched_tracks:
            audio_file = match['audio_file']
            csv_track = match['csv_track']

            # Percorso relativo
            rel_path = f"./{audio_file['path'].name}"

            # Informazioni traccia
            f.write(f"#EXTINF:-1,{csv_track['artist']} - {csv_track['title']}")
            f.write(f"{rel_path}")

    print(f"Playlist creata: {output_path}")


def create_unmatched_report(unmatched_tracks, output_path):
    """Crea un report dei file non matchati"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write("FILE NON MATCHATI")
        f.write("=" * 80 + "")

        for item in unmatched_tracks:
            csv_track = item['csv_track']
            best_match = item['best_match']
            best_score = item['best_score']

            f.write(f"Traccia CSV: {csv_track['row']}")

            if best_match:
                f.write(f"Miglior match: {best_match['path'].name}")
                f.write(f"  Titolo file: {best_match['title']}")
                f.write(f"  Artista file: {best_match['artist']}")
                f.write(f"  Score: {best_score:.2f}")
            else:
                f.write("Nessun file trovato")

            f.write("\n")

    print(f"Report non matchati creato: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Crea una playlist M3U da un file CSV con fuzzy matching'
    )
    parser.add_argument('directory', help='Directory contenente i file audio')
    parser.add_argument('csv_file', help='File CSV con l\'elenco delle tracce')
    parser.add_argument('--output', '-o', default='playlist.m3u',
                        help='Nome file playlist output (default: playlist.m3u)')
    parser.add_argument('--threshold', '-t', type=int, default=70,
                        help='Soglia minima matching (0-100, default: 70)')
    parser.add_argument('--unmatched', '-u', default='unmatched.txt',
                        help='Nome file report non matchati (default: unmatched.txt)')

    args = parser.parse_args()

    # Verifica esistenza directory e CSV
    if not os.path.isdir(args.directory):
        print(f"Errore: directory '{args.directory}' non trovata")
        return

    if not os.path.isfile(args.csv_file):
        print(f"Errore: file CSV '{args.csv_file}' non trovato")
        return

    print("Scansione file audio...")
    audio_files = scan_audio_files(args.directory)

    print("Lettura CSV...")
    csv_tracks = read_csv_tracks(args.csv_file)

    print("Matching tracce...")
    matched, unmatched = match_tracks(csv_tracks, audio_files, args.threshold)

    print(f"Risultati:")
    print(f"  Tracce matchate: {len(matched)}")
    print(f"  Tracce non matchate: {len(unmatched)}")

    if matched:
        create_m3u_playlist(matched, args.output, args.directory)

    if unmatched:
        create_unmatched_report(unmatched, args.unmatched)

    print("Completato!")


if __name__ == '__main__':
    main()
