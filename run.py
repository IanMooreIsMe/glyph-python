from os import environ


def main():
    from glyph import GlyphBot
    g = GlyphBot()
    g.run(environ.get("DISCORD_TOKEN"))


if __name__ == '__main__':
    main()
