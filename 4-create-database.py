import json
import logging
import os
import sqlite3
import signal
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import argparse
from urllib.parse import unquote


class ForvoProcessor:
    def __init__(self, root_dir: str, db_path: str = "forvo_database.db", simple_db_path: str = "forvo_simple.db"):
        self.root_dir = Path(root_dir)
        self.db_path = db_path
        self.simple_db_path = simple_db_path
        self.audio_dir = self.root_dir
        self.metadata_file = self.root_dir / "metadata.jsonl"
        self.icons_dir = self.root_dir / "icons"
        self.country_mappings_file = self.root_dir / "country_mappings.json"
        
        self.setup_logging()
        
        self.country_mappings = self.load_country_mappings()
        
        self.conn = None
        self.simple_conn = None
        
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        self.interrupted = False
    
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('db_processor.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def signal_handler(self, signum, frame):
        self.logger.info(f"Received signal {signum}. Shutting down...")
        self.interrupted = True
        if self.conn:
            self.conn.close()
        if self.simple_conn:
            self.simple_conn.close()
        sys.exit(0)
    
    def load_country_mappings(self) -> Dict[str, Dict]:
        try:
            with open(self.country_mappings_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
            
            country_lookup = {}
            for mapping in mappings:
                country_lookup[mapping['original_name'].lower()] = mapping
            
            self.logger.info(f"Loaded {len(country_lookup)} country mappings")
            return country_lookup
        
        except FileNotFoundError:
            self.logger.error(f"Country mappings file not found: {self.country_mappings_file}")
            return {}
        except json.JSONDecodeError as e:
            self.logger.error(f"Error parsing country mappings: {e}")
            return {}
    
    def init_databases(self):
        try:
            self.conn = sqlite3.connect(self.db_path)
            cursor = self.conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    language TEXT NOT NULL,
                    headword TEXT NOT NULL,
                    html_content TEXT NOT NULL,
                    audio_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(language, headword)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audio_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word_id INTEGER,
                    username TEXT,
                    gender TEXT,
                    country TEXT,
                    votes INTEGER DEFAULT 0,
                    file_path TEXT,
                    download_url TEXT,
                    audio_id INTEGER,
                    FOREIGN KEY (word_id) REFERENCES words (id)
                )
            ''')
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_words_language_headword ON words(language, headword)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audio_word_id ON audio_files(word_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audio_votes ON audio_files(votes DESC)')
            
            self.conn.commit()
            self.logger.info("Complex database initialized successfully")
            
            self.simple_conn = sqlite3.connect(self.simple_db_path)
            simple_cursor = self.simple_conn.cursor()
            
            simple_cursor.execute('''
                CREATE TABLE IF NOT EXISTS mdx (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry TEXT NOT NULL,
                    paraphrase TEXT NOT NULL,
                    language TEXT,
                    audio_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(entry, language)
                )
            ''')
            
            simple_cursor.execute('CREATE INDEX IF NOT EXISTS idx_mdx_entry ON mdx(entry)')
            simple_cursor.execute('CREATE INDEX IF NOT EXISTS idx_mdx_language ON mdx(language)')
            simple_cursor.execute('CREATE INDEX IF NOT EXISTS idx_mdx_entry_language ON mdx(entry, language)')
            
            self.simple_conn.commit()
            self.logger.info("Simple database (MDX format) initialized successfully")
            
        except sqlite3.Error as e:
            self.logger.error(f"Database initialization error: {e}")
            raise
    
    def get_icon_path(self, gender: str, country: str) -> Optional[str]:
        gender_prefix = ""
        if gender and gender.lower() in ['male', 'female']:
            gender_prefix = f"{gender.lower()}_"
        
        country_info = self.country_mappings.get(country.lower())
        if not country_info:
            self.logger.debug(f"Country mapping not found for: {country}")
            return None
        
        iso_code = country_info['iso_code']
        
        icon_patterns = [
            f"{gender_prefix}{iso_code}.svg",
            f"_{iso_code}.svg",
            f"{iso_code}.svg"
        ]
        
        for pattern in icon_patterns:
            icon_path = self.icons_dir / pattern
            if icon_path.exists():
                return f"icons/{pattern}"
        
        self.logger.debug(f"Icon not found for {gender}_{country} (ISO: {iso_code})")
        return None
    
    def check_audio_file_exists(self, language: str, username: str, headword: str) -> Optional[str]:
        extensions = ['.opus', '.mp3', '.ogg']
        
        for ext in extensions:
            audio_path = self.audio_dir / language / username / f"{headword}{ext}"
            if audio_path.exists():
                return f"{language}/{username}/{headword}{ext}"
        
        return None
    
    def generate_html_content(self, audio_data: List[Dict]) -> str:
        html_parts = ['<div class="audio-pronunciations">']
        
        sorted_audio = sorted(audio_data, key=lambda x: x.get('votes', 0), reverse=True)
        
        for audio in sorted_audio:
            username = audio.get('username', 'unknown')
            gender = audio.get('gender', '')
            country = audio.get('country', '')
            votes = audio.get('votes', 0)
            file_path = audio.get('file_path', '')
            
            icon_path = self.get_icon_path(gender, country)
            if not icon_path:
                self.logger.debug(f"No icon found for {username} ({gender}, {country})")
                continue
            
            title_text = f"{username} ({country})"
            if votes > 0:
                title_text += f" - {votes} votes"
            
            audio_html = f'''
            <div class="pronunciation-item">
                <a href="sound://{file_path}" title="{title_text}">
                    <img src="{icon_path}" 
                         alt="{username}" 
                         class="pronunciation-icon" 
                         style="width: 24px; height: 24px; margin: 2px; border: none;">
                </a>
                {f'<span class="vote-count">({votes})</span>' if votes > 0 else ''}
            </div>'''
            
            html_parts.append(audio_html)
        
        if html_parts[1:]:
            html_parts.append('''
            <style>
            .audio-pronunciations {
                display: flex;
                flex-wrap: wrap;
                gap: 5px;
                align-items: center;
            }
            .pronunciation-item {
                display: inline-flex;
                align-items: center;
                gap: 2px;
            }
            .pronunciation-item a {
                text-decoration: none;
                border: none;
                display: inline-block;
            }
            .pronunciation-icon:hover {
                opacity: 0.7;
                transform: scale(1.1);
                transition: all 0.2s ease;
            }
            .vote-count {
                font-size: 0.8em;
                color: #666;
                margin-left: 2px;
            }
            </style>''')
        
        html_parts.append('</div>')
        return ''.join(html_parts)
    
    def process_metadata(self):
        if not self.metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_file}")
        
        self.logger.info("Starting metadata processing...")
        
        word_audio_map = defaultdict(list)
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                line_count = 0
                processed_count = 0
                
                for line in f:
                    if self.interrupted:
                        break
                    
                    line_count += 1
                    if line_count % 10000 == 0:
                        self.logger.info(f"Processed {line_count} metadata entries...")
                    
                    try:
                        entry = json.loads(line.strip())
                        
                        language = entry.get('language', '')
                        headword = entry.get('headword', '')
                        
                        if not language or not headword:
                            continue
                        
                        query_word = entry.get('query_word', headword)
                        if query_word != headword:
                            headword = unquote(query_word)
                        
                        origin = entry.get('origin', [])
                        if len(origin) >= 3:
                            username, gender, country = origin[0], origin[1], origin[2]
                        else:
                            username = origin[0] if origin else 'unknown'
                            gender = origin[1] if len(origin) > 1 else ''
                            country = origin[2] if len(origin) > 2 else ''
                        
                        votes = entry.get('votes', 0)
                        download_url = entry.get('download_url', '')
                        audio_id = entry.get('id', 0)
                        
                        file_path = self.check_audio_file_exists(language, username, headword)
                        if not file_path:
                            self.logger.debug(f"Audio file not found for {language}/{username}/{headword}")
                            continue
                        
                        key = (language, headword)
                        word_audio_map[key].append({
                            'username': username,
                            'gender': gender,
                            'country': country,
                            'votes': votes,
                            'file_path': file_path,
                            'download_url': download_url,
                            'audio_id': audio_id
                        })
                        
                        processed_count += 1
                        
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"Error parsing JSON on line {line_count}: {e}")
                        continue
                    except Exception as e:
                        self.logger.error(f"Error processing line {line_count}: {e}")
                        continue
                
                self.logger.info(f"Processed {processed_count} valid audio entries from {line_count} total lines")
                
        except Exception as e:
            self.logger.error(f"Error reading metadata file: {e}")
            raise
        
        self.logger.info(f"Creating database entries for {len(word_audio_map)} unique words...")
        
        cursor = self.conn.cursor()
        simple_cursor = self.simple_conn.cursor()
        word_count = 0
        
        for (language, headword), audio_list in word_audio_map.items():
            if self.interrupted:
                break
            
            try:
                html_content = self.generate_html_content(audio_list)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO words (language, headword, html_content, audio_count)
                    VALUES (?, ?, ?, ?)
                ''', (language, headword, html_content, len(audio_list)))
                
                word_id = cursor.lastrowid
                
                for audio in audio_list:
                    cursor.execute('''
                        INSERT INTO audio_files 
                        (word_id, username, gender, country, votes, file_path, download_url, audio_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        word_id,
                        audio['username'],
                        audio['gender'],
                        audio['country'],
                        audio['votes'],
                        audio['file_path'],
                        audio['download_url'],
                        audio['audio_id']
                    ))
                
                simple_cursor.execute('''
                    INSERT OR REPLACE INTO mdx (entry, paraphrase, language, audio_count)
                    VALUES (?, ?, ?, ?)
                ''', (headword, html_content, language, len(audio_list)))
                
                word_count += 1
                if word_count % 1000 == 0:
                    self.conn.commit()
                    self.simple_conn.commit()
                    self.logger.info(f"Processed {word_count} words...")
                
            except sqlite3.Error as e:
                self.logger.error(f"Database error for {language}/{headword}: {e}")
                continue
            except Exception as e:
                self.logger.error(f"Error processing {language}/{headword}: {e}")
                continue
        
        self.conn.commit()
        self.simple_conn.commit()
        self.logger.info(f"Successfully processed {word_count} words")
    
    def run(self):
        try:
            self.logger.info("Starting database builder...")
            
            if not self.root_dir.exists():
                raise FileNotFoundError(f"Root directory not found: {self.root_dir}")
            
            if not self.audio_dir.exists():
                raise FileNotFoundError(f"Audio directory not found: {self.audio_dir}")
            
            if not self.icons_dir.exists():
                raise FileNotFoundError(f"Icons directory not found: {self.icons_dir}")
            
            self.init_databases()
            
            self.process_metadata()
            
            if not self.interrupted:
                self.logger.info("Processing completed successfully!")
                
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM words")
                word_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM audio_files")
                audio_count = cursor.fetchone()[0]
                
                simple_cursor = self.simple_conn.cursor()
                simple_cursor.execute("SELECT COUNT(*) FROM mdx")
                mdx_count = simple_cursor.fetchone()[0]
                
                self.logger.info(f"Database statistics:")
                self.logger.info(f"  Complex database ({self.db_path}):")
                self.logger.info(f"    - Total words: {word_count}")
                self.logger.info(f"    - Total audio files: {audio_count}")
                self.logger.info(f"  Simple database ({self.simple_db_path}):")
                self.logger.info(f"    - Total MDX entries: {mdx_count}")
        
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
            raise
        
        finally:
            if self.conn:
                self.conn.close()
            if self.simple_conn:
                self.simple_conn.close()


def main():
    parser = argparse.ArgumentParser(description='Build Forvo audio databases')
    parser.add_argument('root_dir', help='Root directory')
    parser.add_argument('--db-path', default='forvo_database.db', help='Output complex database path')
    parser.add_argument('--simple-db-path', default='forvo_simple.db', help='Output simple database path (MDX format)')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='Logging level')
    
    args = parser.parse_args()
    
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    processor = ForvoProcessor(args.root_dir, args.db_path, args.simple_db_path)
    processor.run()


if __name__ == '__main__':
    main()