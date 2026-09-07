"""
High-accuracy Bijoy (SutonnyMJ / ANSI) to Unicode Bengali Converter.
Transforms legacy ASCII-encoded Bengali documents (e.g. Word .docx, .doc, .rtf)
into modern UTF-8 Unicode Bengali, preserving typography, conjuncts, and vowel signs.
"""
import re

class BijoyToUnicode:
    CONJUNCTS = [
        # 4-char and 3-char conjuncts
        ('†kÖv', 'শ্রো'), ('‡kÖv', 'শ্রো'),
        ('†cÖv', 'প্রো'), ('‡cÖv', 'প্রো'),
        ('†MÖv', 'গ্রো'), ('‡MÖv', 'গ্রো'),
        ('kÖæ', 'শ্রু'), ('cÖæ', 'প্রু'),
        ('MÖ', 'গ্র'), ('cÖ', 'প্র'), ('kÖ', 'শ্র'), ('eª', 'ব্র'), ('fª', 'ভ্র'),
        ('dª', 'ফ্র'), ('Uª', 'ট্র'), ('Vª', 'ঠ্র'), ('Wª', 'ড্র'), ('Xª', 'ঢ্র'),
        ('Yª', 'ণ্র'), ('Z«', 'ত্র'), ('_ª', 'থ্র'), ('`«', 'দ্র'), ('a«', 'ধ্র'),
        ('b«', 'ন্র'), ('m«', 'স্র'), ('h«', 'য্র'), ('l«', 'ষ্র'), ('n«', 'হ্র'),
        ('Lª', 'খ্র'), ('Nª', 'ঘ্র'), ('Qª', 'ছ্র'), ('R«', 'জ্র'), ('S«', 'ঝ্র'),
        ('gª', 'ম্র'), ('j«', 'ল্র'), ('K«', 'ক্র'), ('P«', 'চ্র'),
        ('M„', 'গৃহ'), ('cô', 'পৃ'), ('e„', 'বৃ'), ('f„', 'ভৃ'), ('Z…', 'তৃ'),
        ('`…', 'দৃ'), ('a…', 'ধৃ'), ('b…', 'নৃ'), ('m…', 'সৃ'), ('K…', 'কৃ'),
        ('P…', 'চৃ'), ('j…', 'লৃ'), ('k…', 'শৃ'), ('l…', 'ষৃ'), ('n…', 'হৃ'),
        
        # Sa (¯) conjuncts
        ('¯^', 'স্ব'), ('¯‹', 'স্ক'), ('¯Œ', 'স্ক্র'), ('¯Í', 'স্ত'), ('¯’', 'স্থ'),
        ('¯œ', 'স্ন'), ('¯ú', 'স্প'), ('¯¢', 'স্ফ'), ('¯§', 'স্ম'), ('¯ª', 'স্র'),
        ('¯ø', 'স্ল'),
        
        # Ka, Ga, Pa, Ba, La, Sha, Sha, Ha conjuncts
        ('K¬', 'ক্ল'), ('Mø', 'গ্ল'), ('cø', 'প্ল'), ('eø', 'ব্ল'), ('d¬', 'ফ্ল'),
        ('j¡', 'ল্ব'), ('jø', 'ল্ল'),
        ('k¡', 'শ্ব'), ('k^', 'শ্ব'), ('kœ', 'শ্ন'), ('k¥', 'শ্ম'), ('kø', 'শ্ল'),
        ('l¡', 'ষ্ব'), ('ó', 'ষ্ট'), ('ô', 'ষ্ঠ'), ('ò', 'ষ্ণ'), ('®ú', 'ষ্প'),
        ('®¢', 'ষ্ফ'), ('®§', 'ষ্ম'),
        ('n¡', 'হ্ব'), ('ý', 'হ্ন'), ('þ', 'হ্ম'), ('ü', 'হ্ল'), ('ù', 'হু'), ('û', 'হু'),
        ('R¡', 'জ্ব'), ('¾', 'জ্জ'), ('À', 'জ্ঞ'), ('Á', 'জ্ঞ'),
        ('T¡', 'ঞ্চ'), ('TÃ', 'ঞ্ছ'), ('TÂ', 'ঞ্জ'), ('TŠ', 'ঞ্ছ'),
        ('Yœ', 'ণ্ণ'), ('YÍ', 'ন্ত'), ('Y‘', 'ণ্ড'), ('Y’', 'ণ্ঠ'),
        ('Ë¡', 'ত্ত্ব'), ('Z¡', 'ত্ব'), ('Ë', 'ত্ত'), ('Í', 'ন্ত'), ('’', 'ন্থ'), ('Ü', 'দ্ধ'),
        ('›`', 'ন্দ'), ('›a', 'ন্ধ'), ('›aŸ', 'ন্ধ্ব'), ('b¡', 'ন্ব'), ('bœ', 'ন্ন'),
        ('šÍ', 'ন্ত'), ('š’', 'ন্থ'), ('›', 'ন্দ'),
        ('¤ú', 'ম্প'), ('¤^', 'ম্ব'), ('¤¢', 'ম্ভ'), ('¤§', 'ম্ম'), ('¤ø', 'ম্ল'),
        ('gœ', 'ম্ন'),
        ('¶§', 'ক্ষ্ম'), ('¶œ', 'ক্ষ্ণ'), ('¶', 'ক্ষ'), ('³', 'ক্ত'),
        ('”P', 'চ্চ'), ('”Q', 'চ্ছ'), ('”T', 'চ্ঞ'),
        ('¸', 'গু'), ('»', 'জ্ঞ'), ('½', 'ঞ্চ'), ('¿', 'ঞ্জ'),
        ('Â', 'ঞ্জ'), ('Ã', 'ঞ্ছ'), ('Ä', 'ঞ্চ'), ('Å', 'ট্ট'),
        ('Æ', 'ট্ঠ'), ('Ç', 'ড্ড'), ('È', 'ঢ্ঢ'), ('É', 'ণ্ট'),
        ('Ê', 'ণ্ঠ'), ('Ì', 'ত্থ'), ('Î', 'ত্র'), ('Ï', 'ন্দ'),
        ('Ð', 'ন্ধ'), ('Ñ', 'ন্ন'), ('Ý', '্ব'),
        ('ß', '্ত্ব'), ('à', 'ন্ত্ব'), ('á', 'ঙ্ক'), ('â', 'ঙ্গ'),
        ('ã', 'চ্ছ'), ('ä', 'জ্জ'), ('å', 'জ্ঝ'), ('æ', 'ট্ট'),
        ('ç', 'ট্ঠ'), ('è', 'ড্ড'), ('é', 'ণ্ণ'), ('ê', 'ত্থ'),
        ('ë', 'দ্ম'), ('ì', 'দ্ব'), ('í', 'ধ্ব'), ('î', 'ন্ম'),
        ('ï', 'ম্প'), ('ð', 'ম্ব'), ('ñ', 'ম্ভ'), ('õ', 'ণ্ড'),
        ('ö', 'গ্ধ'), ('ú', 'স্প'), ('ÿ', 'ক্ষ'), ('µ', 'ক্র'),
        ('÷', 'ষ্ট'), ('Ø', 'দ্ব'), ('¥', '্ম')
    ]

    CHARS = {
        # Digits
        '0': '০', '1': '১', '2': '২', '3': '৩', '4': '৪',
        '5': '৫', '6': '৬', '7': '৭', '8': '৮', '9': '৯',
        # Consonants
        'K': 'ক', 'L': 'খ', 'M': 'গ', 'N': 'ঘ', 'O': 'ঙ',
        'P': 'চ', 'Q': 'ছ', 'R': 'জ', 'S': 'ঝ', 'T': 'ঞ',
        'U': 'ট', 'V': 'ঠ', 'W': 'ড', 'X': 'ঢ', 'Y': 'ণ',
        'Z': 'ত', '_': 'থ', '`': 'দ', 'a': 'ধ', 'b': 'ন',
        'c': 'প', 'd': 'ফ', 'e': 'ব', 'f': 'ভ', 'g': 'ম',
        'h': 'য', 'i': 'র', 'j': 'ল', 'k': 'শ', 'l': 'ষ',
        'm': 'স', 'n': 'হ', 'o': 'ড়', 'p': 'ঢ়', 'q': 'য়',
        # Vowels
        'A': 'অ', 'B': 'ই', 'C': 'ঈ', 'D': 'উ', 'E': 'ঊ',
        'F': 'ঋ', 'G': 'এ', 'H': 'ঐ', 'I': 'ও', 'J': 'ঔ',
        # Kars
        'v': 'া', 'x': 'ী', 'y': 'ু', '~': 'ূ', '…': 'ৃ', '„': 'ৃ',
        # Modifiers & signs
        'r': 'ৎ', 's': 'ং', 't': 'ঃ', 'u': 'ঁ',
        '|': '।', 'Ó': '"', 'Ò': '"', 'Ô': '—', 'Õ': "'", 'Ù': "'", 'Ú': "'", 'Û': "'",
        '¨': '্য', 'Ö': '্র', '&': '্', 'ª': '্র', '«': '্র',
        '¶': 'ক্ষ', '³': 'ক্ত', 'Î': 'ত্র', 'Ø': 'দ্ব', 'ì': 'দ্ব',
        '÷': 'ষ্ট', '¥': '্ম'
    }

    @classmethod
    def convert(cls, text: str) -> str:
        if not text:
            return ""

        # Ensure multi-char conjuncts match before single glyphs
        if not hasattr(cls, '_sorted_conjuncts'):
            cls._sorted_conjuncts = sorted(cls.CONJUNCTS, key=lambda x: len(x[0]), reverse=True)

        # Step 1: Replace complex multi-character conjuncts (longest first)
        for b_c, u_c in cls._sorted_conjuncts:
            text = text.replace(b_c, u_c)

        # Step 2: Ref handler (in SutonnyMJ, \xa9 / © is placed after consonant/cluster)
        # Convert to র্ before the consonant cluster
        text = re.sub(r'([\w\u0080-\u00ff\u0980-\u09ff&_`^~])\xa9', r'র্\1', text)

        # Step 3: o-kar and ou-kar ([†‡] + cons + v -> cons + ো)
        text = re.sub(
            r'([†‡\u2020\u2021])((?:র্)?[\w\u0080-\u00ff\u0980-\u09ff&_`^~](?:[্&][\w\u0080-\u00ff\u0980-\u09ff&_`^~])?)v',
            r'\2ো',
            text
        )
        text = re.sub(
            r'([†‡\u2020\u2021])((?:র্)?[\w\u0080-\u00ff\u0980-\u09ff&_`^~](?:[্&][\w\u0080-\u00ff\u0980-\u09ff&_`^~])?)Š',
            r'\2ৌ',
            text
        )

        # Step 4: Pre-kars (w -> ি, †/‡ -> ে, ‰ -> ৈ)
        def _repl_pre(m):
            kar = m.group(1)
            cons = m.group(2)
            uni_kar = 'ি' if kar == 'w' else ('ে' if kar in ('†', '‡', '\u2020', '\u2021') else 'ৈ')
            return cons + uni_kar

        pattern = r'([w†‡‰\u2020\u2021\u2030])((?:র্)?[\w\u0080-\u00ff\u0980-\u09ff&_`^~](?:[্&][\w\u0080-\u00ff\u0980-\u09ff&_`^~])?)'
        text = re.sub(pattern, _repl_pre, text)

        # Step 5: Map individual characters
        res = []
        for ch in text:
            res.append(cls.CHARS.get(ch, ch))
        out = ''.join(res)

        # Step 6: Typography cleanups
        out = out.replace('অা', 'আ')
        out = out.replace('্্', '্')
        return out

    @staticmethod
    def is_sutonny_font(font_name: str) -> bool:
        if not font_name:
            return False
        fn = font_name.lower()
        return any(k in fn for k in ('sutonny', 'bijoy', 'boishakhi', 'chandan', 'shurjomukhi', 'probhat'))

    @classmethod
    def has_bijoy_markers(cls, text: str) -> bool:
        """Heuristic check to determine if an ASCII string is Bijoy/SutonnyMJ encoded text."""
        if not text or len(text) < 3:
            return False
        # Distinctive Bijoy patterns
        markers = ('wemw', 'jø', '¯‹', '¯Í', '†`', '‡`', 'cÖ', 'MÖ', 'd¨', 'e¨', 'c¶', '`wjj', 'ag©', 'kZ©')
        return any(m in text for m in markers)
