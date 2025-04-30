/*
 * AJT Japanese JS 25.4.30.1
 * Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
 * License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.html
 */

(function () {
    "use strict";

    function ajt__kana_to_moras(text) {
        return text.match(/.[°゚]?[ァィゥェォャュョぁぃぅぇぉゃゅょ]?/gu);
    }

    function ajt__norm_handakuten(text) {
        return text.replace(/\u{b0}/gu, "\u{309a}");
    }

    function ajt__make_pattern(kana, pitch_type, pitch_num) {
        const moras = ajt__kana_to_moras(ajt__norm_handakuten(kana));
        switch (pitch_type) {
            case "atamadaka":
                return (
                    `<span class="ajt__HL">${moras[0]}</span>` +
                    `<span class="ajt__L">${moras.slice(1).join("")}</span>` +
                    `<span class="ajt__pitch_number_tag">1</span>`
                );
                break;
            case "heiban":
                return (
                    `<span class="ajt__LH">${moras[0]}</span>` +
                    `<span class="ajt__H">${moras.slice(1).join("")}</span>` +
                    `<span class="ajt__pitch_number_tag">0</span>`
                );
                break;
            case "odaka":
                return (
                    `<span class="ajt__LH">${moras[0]}</span>` +
                    `<span class="ajt__HL">${moras.slice(1).join("")}</span>` +
                    `<span class="ajt__pitch_number_tag">${moras.length}</span>`
                );
                break;
            case "nakadaka":
                return (
                    `<span class="ajt__LH">${moras[0]}</span>` +
                    `<span class="ajt__HL">${moras.slice(1, Number(pitch_num)).join("")}</span>` +
                    `<span class="ajt__L">${moras.slice(Number(pitch_num)).join("")}</span>` +
                    `<span class="ajt__pitch_number_tag">${pitch_num}</span>`
                );
                break;
        }
    }

    function ajt__format_new_ruby(kanji, readings) {
        if (readings.length > 1) {
            return `<ruby>${ajt__format_new_ruby(kanji, readings.slice(0, -1))}</ruby><rt>${readings.slice(-1)}</rt>`;
        } else {
            return `${kanji}<rt>${readings.join("")}</rt>`;
        }
    }

    function ajt__zip(array1, array2) {
        let zipped = [];
        const size = Math.min(array1.length, array2.length);
        for (let i = 0; i < size; i++) {
            zipped.push([array1[i], array2[i]]);
        }
        return zipped;
    }

    function ajt__make_accent_list_item(kana_reading, pitch_accent) {
        // If the word is a compound, pitch accents come separated by commas.
        // The reading is also divided into sections with nakaten.
        // Example input: キシ・カイセイ:nakadaka-2,heiban
        const list_item = document.createElement("li");
        for (const [reading_part, pitch_part] of ajt__zip(kana_reading.split("・"), pitch_accent.split(","))) {
            // Pitch number is specified only for nakadaka words, after a dash.
            const [pitch_type, pitch_num] = pitch_part.split("-");
            const pattern = ajt__make_pattern(reading_part, pitch_type, pitch_num);
            list_item.insertAdjacentHTML("beforeend", `<span class="ajt__downstep_${pitch_type}">${pattern}</span>`);
        }
        return list_item;
    }

    function ajt__make_accents_list(ajt_span) {
        const accents = document.createElement("ul");
        // Example input: ワタクシ:heiban ワタシ:heiban アタシ:heiban
        for (const accent_group of ajt_span.getAttribute("pitch").split(" ")) {
            accents.appendChild(ajt__make_accent_list_item(...accent_group.split(":")));
        }
        return accents;
    }

    function ajt__make_popup_div(content) {
        /* Popup Top frame */
        const frame_top = document.createElement("div");
        frame_top.classList.add("ajt__frame_title");
        frame_top.innerText = "Information";

        /* Popup Content */
        const frame_bottom = document.createElement("div");
        frame_bottom.classList.add("ajt__frame_content");
        frame_bottom.appendChild(content);

        /* Make Popup */
        const popup = document.createElement("div");
        popup.classList.add("ajt__info_popup");
        popup.appendChild(frame_top);
        popup.appendChild(frame_bottom);
        return popup;
    }

    function ajt__find_word_info_popup(word_span) {
        return word_span.querySelector(".ajt__info_popup");
    }

    function ajt__find_popup_x_corners(popup_div) {
        const elem_rect = popup_div.getBoundingClientRect();
        const right_corner_x = elem_rect.x + elem_rect.width;
        return {
            x_start: elem_rect.x,
            x_end: right_corner_x,
            shifted_x_start: elem_rect.x + elem_rect.width / 2,
            shifted_x_end: right_corner_x + elem_rect.width / 2,
        };
    }

    function ajt__word_info_on_mouse_enter(word_span) {
        const popup_div = ajt__find_word_info_popup(word_span);
        if (popup_div) {
            ajt__word_info_on_mouse_leave(word_span);
            const x_pos = ajt__find_popup_x_corners(popup_div);
            if (x_pos.x_start < 0) {
                popup_div.classList.add("ajt__left-corner");
                popup_div.style.setProperty("--shift-x", `${Math.ceil(-x_pos.x_start)}px`);
            } else if (x_pos.shifted_x_end < window.innerWidth) {
                popup_div.classList.add("ajt__in-middle");
            }
        }
    }

    function ajt__word_info_on_mouse_leave(word_span) {
        const popup_div = ajt__find_word_info_popup(word_span);
        if (popup_div) {
            popup_div.classList.remove("ajt__left-corner", "ajt__in-middle");
        }
    }

    function ajt__adjust_popup_position_on_mouse_enter(word_info_span) {
        /* React to mouse enter and leave */
        word_info_span.addEventListener("mouseenter", (event) => ajt__word_info_on_mouse_enter(event.currentTarget));
        word_info_span.addEventListener("mouseleave", (event) => ajt__word_info_on_mouse_leave(event.currentTarget));
    }

    function ajt__format_readings_as_list(readings) {
        const readings_items = readings.map((reading) => `<li>${reading}</li>`).join("");
        const list_elem = document.createElement("ol");
        list_elem.classList.add("ajt__readings_list");
        list_elem.insertAdjacentHTML("beforeend", readings_items);
        return list_elem;
    }

    function ajt__fixup_br(element) {
        // If there's a <br> tag inside the reading, e.g. <ruby><rb>矜持</rb><rt>きょうじ<br>きんじ</rt></ruby>,
        // then replace it with a space.
        element.querySelectorAll("br").forEach((element) => {
            element.insertAdjacentText("afterend", " ");
            element.remove();
        });
        return element;
    }

    function ajt__find_kanji_readings(ruby_tag) {
        // <rb> contains the kanji word (on some platforms). <rt> contains the kana reading(s) (furigana).
        const separators = /[\n\s;,.、・。]+/iu;
        const kanji = (ruby_tag.querySelector("rb") || ruby_tag.firstChild).textContent.trim();
        const readings = ajt__fixup_br(ruby_tag.querySelector("rt"))
            .textContent.split(separators)
            .map((str) => str.trim())
            .filter((str) => str.length);
        return { kanji: kanji, readings: readings };
    }

    function ajt__reformat_multi_furigana() {
        const max_inline = 2;
        document.querySelectorAll("ruby:not(ruby ruby):not(.ajt__furigana_list ruby)").forEach((ruby) => {
            // Skip elements that already have stacked furigana.
            try {
                const { kanji, readings } = ajt__find_kanji_readings(ruby);
                if (readings.length > 1) {
                    // Stack the first few readings on top of each other to save horizontal space.
                    ruby.innerHTML = ajt__format_new_ruby(kanji, readings.slice(0, max_inline));
                }
                if (readings.length > max_inline && !ruby.matches(".ajt__word_info ruby")) {
                    // If the word has a lot of readings, show them on mouseover.
                    // Don't add popups to color-coded blocks of text. They already have their own popups.
                    const content_ul = ajt__format_readings_as_list(readings);
                    const popup = ajt__make_popup_div(content_ul);
                    const wrapper = document.createElement("span");
                    ruby.replaceWith(wrapper);
                    wrapper.appendChild(ruby);
                    wrapper.appendChild(popup);
                    wrapper.classList.add("ajt__furigana_list");
                    ajt__adjust_popup_position_on_mouse_enter(wrapper);
                }
            } catch (error) {
                console.error(error);
            }
        });
    }

    function ajt__create_popups() {
        for (const [idx, span] of document.querySelectorAll(".ajt__word_info").entries()) {
            if (span.matches(".jpsentence .background *")) {
                // Fix for "Japanese sentences" note type.
                continue;
            }
            if (ajt__find_word_info_popup(span)) {
                // The popup exists. This tag has been handled already.
                continue;
            }
            try {
                const content_ul = ajt__make_accents_list(span);
                const popup = ajt__make_popup_div(content_ul);
                popup.setAttribute("ajt__popup_idx", idx);
                span.setAttribute("ajt__popup_idx", idx);
                span.appendChild(popup);
                ajt__adjust_popup_position_on_mouse_enter(span);
            } catch (error) {
                console.error(error);
            }
        }
    }

    /* Setup */
    function ajt__main() {
        ajt__create_popups();
        ajt__reformat_multi_furigana();
    }

    if (document.readyState === "loading") {
        // Loading hasn't finished yet
        document.addEventListener("DOMContentLoaded", ajt__main);
    } else {
        // `DOMContentLoaded` has already fired
        ajt__main();
    }
})();
