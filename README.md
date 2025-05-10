# 📙 Emobble: Emoji Support for Scribble
### -Render me Emobble-

**Emobble** is a plug-in extension for the [Scribble](https://github.com/jujuadams/scribble) text rendering library in GameMaker. It adds seamless emoji support to your in-game text using texture atlases, custom glyph injection, and smart parsing. Simply including Emobble in your projects will add emoji support to native `scribble()` functionality.

---

### 📌 Features

- ✅ Full Unicode emoji support via image-based atlases
- ⚡ Fast lookup and rendering performance
- 🧩 Drop-in integration with existing Scribble-based systems
- 📦 Includes pre-packed emoji sheets (Twemoji / Noto / etc)
- 🧠 Smart fallback and missing-glyph handling
- 🔍 Optional search/filter utilities for emoji input
- ✂️ Scalable architecture (support for custom emoji sets or styles)

---

### 📂 Installation

1. Download the latest release from the [Releases](https://github.com/tinkerer-red/Emobble/releases) page.
2. Import Emobble GameMaker project.
3. Edit the Config script `__Emobble_Config` to contain the atlas and look up tables you wish to use.
4. (optional) change Scribble configs `SCRIBBLE_AUTOFIT_INLINE_TEXTURES` and `SCRIBBLE_SPRITE_BILINEAR_FILTERING` to `true`
5. Use Scribble as normal—Emobble will automatically parse and render emoji codes

---

### 🛠️ Usage Example

```gml
scribble("Hello world! 😎👍").draw(32, 32);
```

You can also make use of [Emobble’s Shortcodes Data Base](https://github.com/tinkerer-red/Emobble/tree/master/Tools/db/Shortcodes) to query emoji short codes like `:smile:` for a variety of languages. Or use the provided [emoji.json](https://github.com/tinkerer-red/Emobble/blob/master/Tools/db/emoji.json) for displaying much more information about emojis, such as Name, Description, and Category.
Great addition. Here's an updated and more complete version of that section with the extra info clearly stated:

> 💡 **Using a Custom Scribble Preprocessor?**  
> If you override the default Scribble preprocessor, make sure to call Emobble's handler inside it:
> 
> ```gml
> _string = scribblify_emojis(_string, EMOBBLE_ATLAS_SPRITE, EMOBBLE_ATLAS_LOOKUP);
> ```
> 
> This ensures emoji parsing still happens with your custom logic.

---

### 🗂️ Emoji Sets

Out of the box, Emobble supports a wide variety of emoji sets, some of the more notable ones include:

- [OpenMoji (FOSS)](https://github.com/tinkerer-red/Emobble/blob/master/Emobble/sprites/emj_spr_openmoji_deluxe_32/59e4113f-32c3-4ec6-a4ac-9ed4470a329f.png)
- [Noto Emoji (Google)](https://github.com/tinkerer-red/Emobble/blob/master/Emobble/sprites/emj_spr_noto_deluxe_32/80bae39c-9e0b-4a46-afcf-2985ed445661.png)
- [SegoeUI (Microsoft)](https://github.com/tinkerer-red/Emobble/blob/master/Emobble/sprites/emj_spr_segoeUi_deluxe_32/7b2a7c59-617b-4843-898e-093a16f7c9fd.png)
- [Twemoji (Twitter)](https://github.com/tinkerer-red/Emobble/blob/master/Emobble/sprites/emj_spr_twemoji_deluxe_32/63a28f7d-2cd0-4a4a-8582-46e9b57d2769.png)    

Each set includes optimized sprite sheets and metadata tailored for GameMaker. Licenses and use cases can be found at the bottom of this README, or a full table can be found [HERE](https://github.com/tinkerer-red/Emobble/blob/master/Emoji%20Ref%20Table.md)

---

### 🚧 Limitations

- Emobble is image-based, so all emoji are raster textures, so the animated emoji sets are not supported.
- Full Unicode emoji range is supported **only if** the atlas and lookup table includes them.

---

### 📄 License

MIT (and/or whatever applies to both Emobble and bundled emoji assets)
(I'd just like a mention in the credits and you're probably fine)

---

### 🙌 Credits

- [Scribble by Juju Adams](https://github.com/jujuadams/scribble) By far the best text renderer for GameMaker and a huge support in getting Texture format tags added to Scribble.
- [Emojipedia](https://emojipedia.org) This project would not be possible with out their incredible dedication to cataloging all of this information in one place.
- And all of the emoji sets included which will have links and references provided below.

---

### Quick Reference for emoji sets
| Emoji Set                                           | Emoji Count                | Open Source   | License Type                             | Allowed in Commercial Video Games (Platform-Specific) | Allowed in Commercial Video Games (Any Platform) | License                                                                                                                     | Source                                                                                                           |
| --------------------------------------------------- | -------------------------- | ------------- | ---------------------------------------- | ----------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Openmoji**                                        | 3808                       | Yes           | Creative Commons Share Alike License 4.0 | Yes                                                   | Yes                                              | [OpenMoji License](https://openmoji.org/faq/)                                                                               | [OpenMoji Website](https://openmoji.org)                                                                         |
| **Google - Noto**                                   | Color: 3815<br>Mono: 3667  | Yes           | SIL Open Font License 1.1                | Yes                                                   | Yes                                              | [Google Noto Emoji License](https://github.com/googlei18n/noto-emoji/blob/master/LICENSE)                                   | [Noto Emoji - Google Fonts](https://fonts.google.com/noto/specimen/Noto+Emoji/license)                           |
| **Microsoft - Segoe UI (Windows 10)**               | Color: 3529<br>Mono: 3667  | Yes           | MIT License                              | Yes                                                   | Yes (only for digital goods)                     | [Segoe UI License](https://learn.microsoft.com/en-us/typography/font-list/segoe-ui-emoji#licensing-and-redistribution-info) | [Segoe UI - Microsoft Typography](https://docs.microsoft.com/en-us/typography/font-list/segoe-ui)                |
| **Microsoft - Fluent 3D, Fluent Flat (Windows 11)** | 3D: 3156<br>Flat: 4373<br> | Yes           | MIT License                              | Yes                                                   | Yes (only for digital goods)                     | [Microsoft Fluent Emoji License](https://github.com/microsoft/fluentui-emoji/blob/main/LICENSE)                             | [Microsoft Fluentui Emoji Github](https://github.com/microsoft/fluentui-emoji)                                   |
| **Twitter - Twemoji**                               | 1830                       | Yes           | MIT License                              | Yes                                                   | Yes                                              | [Twemoji on GitHub License](https://github.com/twitter/twemoji/blob/master/LICENSE)                                         | [Twemoji on GitHub](https://github.com/twitter/twemoji)                                                          |
| **emojidex**                                        | 2025                       | Yes           | Apache License 2.0                       | Yes                                                   | Yes                                              | [Emojidex License](https://github.com/holepunchto/emoji-index/blob/main/LICENSE)                                            | [emojidex](https://www.emojidex.com)                                                                             |
| **Icons8**                                          | 2117                       | Yes           | Universal Multimedia License Agreement   | Yes                                                   | Yes                                              | [Icons8 License](https://icons8.com/license)                                                                                | [Icons8 Licensing](https://icons8.com/license)                                                                   |
A more complete table can be found [here](https://github.com/tinkerer-red/Emobble/blob/master/Emoji%20Ref%20Table.md)
