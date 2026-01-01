import pdfplumber

def extract_pdf_layout(pdf_path):
    """
    Extract words with coordinates using PDFPlumber's layout-aware extraction.
    Reconstructs multi-word scientific terms BEFORE ontology lookup.
    """

    pages_output = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):

            # --- STEP 1: Extract raw words from PDFPlumber ---
            raw_words = page.extract_words(
                keep_blank_chars=False,
                use_text_flow=True,
                extra_attrs=["fontname", "size"]
            )

            words = []

            # Convert PDFPlumber word dicts into your unified structure
            for w in raw_words:
                words.append({
                    "text": w["text"],
                    "x": float(w["x0"]),
                    "y": float((w["top"] + w["bottom"]) / 2),  # FIXED: center y for highlight alignment
                    "width": float(w["x1"] - w["x0"]),
                    "height": float(w["bottom"] - w["top"]),
                    "block": 0,
                    "line": 0,
                    "word_no": 0
                })

            # --- STEP 2: Merge hyphenated words across line breaks ---
            merged_words = []
            skip_next = False

            for i in range(len(words)):
                if skip_next:
                    skip_next = False
                    continue

                current = words[i]
                text = current["text"]

                if text.endswith("-") and i + 1 < len(words):
                    next_word = words[i + 1]
                    merged_text = text.rstrip("-") + next_word["text"]

                    merged_word = current.copy()
                    merged_word["text"] = merged_text

                    merged_words.append(merged_word)
                    skip_next = True
                else:
                    merged_words.append(current)

            words = merged_words

            # --- STEP 3: Phrase reconstruction (FIXED) ---
            phrases = []
            current_phrase = []

            def flush_phrase():
                if len(current_phrase) > 0:
                    phrase_text = " ".join([w["text"] for w in current_phrase])
                    phrases.append({
                        "text": phrase_text,
                        "words": current_phrase.copy()
                    })

            for i, w in enumerate(words):
                raw = w["text"]
                token = raw.strip().strip(".,;:()[]{}")
                token = token.replace("\u200b", "").replace("\u00ad", "").replace("\u2011", "")

                is_valid_token = (
                    token.isalpha() or
                    "-" in token or
                    token.isalnum()
                )

                if is_valid_token:
                    if not current_phrase:
                        current_phrase = [w]
                    else:
                        prev = current_phrase[-1]

                        # FIXED: use y proximity for line match
                        same_line = abs(prev["y"] - w["y"]) < 5

                        # FIXED: use x proximity for adjacency
                        horizontal_gap = w["x"] - (prev["x"] + prev["width"])
                        adjacent = 0 <= horizontal_gap < 30  # tuned threshold

                        if same_line and adjacent:
                            current_phrase.append(w)
                        else:
                            flush_phrase()
                            current_phrase = [w]
                else:
                    flush_phrase()
                    current_phrase = []

            flush_phrase()

            # --- DEBUG: inspect phrases containing key terms ---
            print("\n=== DEBUG PHRASES (page", page_index + 1, ") ===")
            for p in phrases:
                if any(k in p["text"].lower() for k in ["otitis", "media", "uvrc", "xby", "mycoplasma", "gene", "strain"]):
                    print("PHRASE:", p["text"])

            # --- STEP 4: Save page output ---
            pages_output.append({
                "page_number": page_index + 1,
                "width": page.width,
                "height": page.height,
                "words": words,
                "phrases": phrases
            })

    return pages_output
