"""
Database Module for Video Maker

Stores:
- Generated Remotion code (for reuse/video library)
- Video metadata (input, output path, timestamp)
- Generation history for analytics

Uses SQLite for simplicity - no external database needed.
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class VideoRecord:
    """A record of a generated video"""
    id: Optional[int]
    created_at: str
    input_content: str
    input_hook: str
    input_duration: int
    input_pacing: str  # JSON string
    input_keywords: str  # JSON string
    generated_code: str
    video_path: str
    status: str  # 'success', 'failed', 'pending'


class VideoDatabase:
    """
    SQLite database for storing generated videos and code.
    
    This serves as:
    1. Backup of all generated code
    2. Video library for code reuse
    3. History/analytics of generations
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize the database
        
        Args:
            db_path: Path to SQLite database file
        """
        if db_path is None:
            # Default: store in project root
            project_root = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(project_root, "video_maker.db")
        
        self.db_path = db_path
        self._init_db()
        print(f"[DATABASE] Initialized at {self.db_path}")
    
    def _init_db(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                input_content TEXT NOT NULL,
                input_hook TEXT,
                input_duration INTEGER,
                input_pacing TEXT,
                input_keywords TEXT,
                generated_code TEXT NOT NULL,
                video_path TEXT,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        # Index for searching by content/hook
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_videos_hook 
            ON videos(input_hook)
        ''')
        
        conn.commit()
        conn.close()
    
    def save_video(
        self,
        input_content: str,
        input_hook: str,
        input_duration: int,
        input_pacing: dict,
        input_keywords: dict,
        generated_code: str,
        video_path: str = None,
        status: str = "success"
    ) -> int:
        """
        Save a video record to the database
        
        Returns:
            The ID of the inserted record
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO videos (
                created_at, input_content, input_hook, input_duration,
                input_pacing, input_keywords, generated_code, video_path, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            datetime.now().isoformat(),
            input_content,
            input_hook,
            input_duration,
            json.dumps(input_pacing),
            json.dumps(input_keywords),
            generated_code,
            video_path,
            status
        ))
        
        video_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        print(f"[DATABASE] ✓ Saved video record #{video_id}")
        return video_id
    
    def get_video(self, video_id: int) -> Optional[VideoRecord]:
        """Get a video record by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return VideoRecord(
                id=row[0],
                created_at=row[1],
                input_content=row[2],
                input_hook=row[3],
                input_duration=row[4],
                input_pacing=row[5],
                input_keywords=row[6],
                generated_code=row[7],
                video_path=row[8],
                status=row[9]
            )
        return None
    
    def get_all_videos(self, limit: int = 100) -> List[VideoRecord]:
        """Get all video records, most recent first"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM videos ORDER BY created_at DESC LIMIT ?',
            (limit,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            VideoRecord(
                id=row[0],
                created_at=row[1],
                input_content=row[2],
                input_hook=row[3],
                input_duration=row[4],
                input_pacing=row[5],
                input_keywords=row[6],
                generated_code=row[7],
                video_path=row[8],
                status=row[9]
            )
            for row in rows
        ]
    
    def search_by_hook(self, hook_keyword: str) -> List[VideoRecord]:
        """Search videos by hook text (for code reuse)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT * FROM videos WHERE input_hook LIKE ? AND status = "success"',
            (f'%{hook_keyword}%',)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [
            VideoRecord(
                id=row[0],
                created_at=row[1],
                input_content=row[2],
                input_hook=row[3],
                input_duration=row[4],
                input_pacing=row[5],
                input_keywords=row[6],
                generated_code=row[7],
                video_path=row[8],
                status=row[9]
            )
            for row in rows
        ]
    
    def get_successful_codes(self, limit: int = 10) -> List[str]:
        """
        Get recent successful generated codes (for video library/examples)
        
        Returns:
            List of generated code strings
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT generated_code FROM videos 
            WHERE status = 'success' 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [row[0] for row in rows]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM videos')
        total = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM videos WHERE status = "success"')
        success = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM videos WHERE status = "failed"')
        failed = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_videos": total,
            "successful": success,
            "failed": failed,
            "success_rate": f"{(success/total*100):.1f}%" if total > 0 else "N/A"
        }


# ============================================================
# HELPER: Generate unique video filename and timestamp ID
# ============================================================

def generate_timestamp_id() -> str:
    """
    Generate a unique timestamp ID for organizing files.
    
    Returns:
        Timestamp string like '20240115_143052'
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def generate_video_filename(prefix: str = "video", timestamp_id: str = None) -> str:
    """
    Generate a unique video filename with timestamp
    
    Args:
        prefix: Filename prefix (default: "video")
        timestamp_id: Optional timestamp to use. If not provided, generates new one.
    
    Returns:
        Filename like 'video_20240115_143052.mp4'
    """
    if timestamp_id is None:
        timestamp_id = generate_timestamp_id()
    return f"{prefix}_{timestamp_id}.mp4"


# ============================================================
# TESTING
# ============================================================

if __name__ == "__main__":
    # Test the database
    db = VideoDatabase()
    
    # Save a test record
    video_id = db.save_video(
        input_content="Test content",
        input_hook="TEST HOOK",
        input_duration=5,
        input_pacing={0: "Line 1", 1: "Line 2"},
        input_keywords={"test": {"color": "#FF0000"}},
        generated_code="// Test code\nexport const Test = () => <div>Test</div>;",
        video_path="/out/test_video.mp4",
        status="success"
    )
    
    print(f"\nSaved video with ID: {video_id}")
    
    # Retrieve it
    record = db.get_video(video_id)
    print(f"Retrieved: {record.input_hook}")
    
    # Get stats
    stats = db.get_stats()
    print(f"\nStats: {stats}")
    
    # Test filename generation
    filename = generate_video_filename()
    print(f"\nGenerated filename: {filename}")
