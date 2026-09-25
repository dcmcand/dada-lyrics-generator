from dada_generator.assembler import Song


def render(song: Song) -> str:
    """Format a song as a plain-text lyric sheet."""
    blocks = []
    for section in song.sections:
        header = f"[{section.name.title()}]"
        blocks.append("\n".join([header, *(line.text for line in section.lines)]))
    return "\n\n".join(blocks) + "\n"
