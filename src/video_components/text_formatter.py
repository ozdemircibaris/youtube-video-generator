"""
Text formatter for preparing and formatting text for video display.
"""

import src.config as config

class TextFormatter:
    def __init__(self, language_code='en', is_shorts=False):
        """
        Initialize the text formatter.
        
        Args:
            language_code (str): Language code for font selection
            is_shorts (bool): Whether formatting is for YouTube Shorts
        """
        self.language_code = language_code
        self.is_shorts = is_shorts
        
        # Set text properties based on video type
        if is_shorts:
            self.font_size = int(config.TEXT_FONT_SIZE * 0.8)  # Slightly smaller for vertical format
            self.max_words_per_line = 3  # Fewer words per line for vertical format
        else:
            self.font_size = config.TEXT_FONT_SIZE
            self.max_words_per_line = config.MAX_WORDS_PER_LINE
            
        self.max_lines = config.MAX_LINES
        
    def group_words_into_segments(self, word_timings):
        """
        Group words into logical segments for display.
        
        Args:
            word_timings (list): List of word timing information
            
        Returns:
            list: List of segments with start time, end time, and words
        """
        if not word_timings:
            return []
        
        segments = []
        current_segment = {
            'words': [],
            'start_time': word_timings[0]['start_time'],
            'end_time': None
        }
        
        # Track words in the current segment
        current_word_count = 0
        
        for word_info in word_timings:
            # Skip marker words
            word = word_info.get('word', '')
            if '_start' in word or '_end' in word:
                continue
                
            # Start a new segment if we've reached the max words per segment
            if current_word_count >= self.max_words_per_line * self.max_lines:
                # Finalize current segment
                if current_segment['words']:
                    last_word = current_segment['words'][-1]
                    current_segment['end_time'] = last_word['end_time']
                    segments.append(current_segment)
                
                # Start a new segment
                current_segment = {
                    'words': [word_info],
                    'start_time': word_info['start_time'],
                    'end_time': None
                }
                current_word_count = 1
            else:
                # Add to current segment
                current_segment['words'].append(word_info)
                current_word_count += 1
        
        # Add the last segment if it has any words
        if current_segment['words']:
            last_word = current_segment['words'][-1]
            current_segment['end_time'] = last_word['end_time']
            segments.append(current_segment)
        
        return segments
        
    def format_text_into_lines(self, text):
        """
        Format text into lines with maximum words per line.
        
        Args:
            text (str): Text to format
            
        Returns:
            list: List of formatted text lines
        """
        if not text:
            return []
            
        words = text.split()
        lines = []
        
        # Format text into lines with max_words_per_line
        for i in range(0, len(words), self.max_words_per_line):
            line = ' '.join(words[i:i + self.max_words_per_line])
            lines.append(line)
        
        # Limit to max_lines
        return lines[:self.max_lines] 