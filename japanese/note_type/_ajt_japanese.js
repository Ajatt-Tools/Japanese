/*
 * AJT Japanese JS 24.7.1.0
 * Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
 * License: GNU AGPL, version 3 or later; https://www.gnu.org/licenses/agpl-3.0.html
 */

function ajt__kana_to_moras(text) {
    return text.match(/.゚?[ァィゥェォャュョぁぃぅぇぉゃゅょ]?/gu);
}

function ajt__make_pattern(kana, pitch_type, pitch_num) {
    const moras = ajt__kana_to_moras(kana);
    switch (pitch_type) {
        case "atamadaka":
            return (
                `<span class="ajt__HL">${moras[0]}</span>` +
                `<span class="ajt__L">${moras.slice(1).join("")}</span> (1)`
            );
            break;
        case "heiban":
            return (
                `<span class="ajt__LH">${moras[0]}</span>` +
                `<span class="ajt__H">${moras.slice(1).join("")}</span> (0)`
            );
            break;
        case "odaka":
            return (
                `<span class="ajt__LH">${moras[0]}</span>` +
                `<span class="ajt__HL">${moras.slice(1).join("")}</span> (${moras.length})`
            );
            break;
        case "nakadaka":
            return (
                `<span class="ajt__LH">${moras[0]}</span>` +
                `<span class="ajt__HL">${moras.slice(1, Number(pitch_num)).join("")}</span>` +
                `<span class="ajt__L">${moras.slice(Number(pitch_num)).join("")}</span> (${pitch_num})`
            );
            break;
    }
}

function ajt__format_new_ruby(kanji, readings) {
    if (readings.length > 1) {
        return `<ruby>${ajt__format_new_ruby(kanji, readings.slice(0, -1))}</ruby><rt>${readings.slice(-1)}</rt>`;
    } else {
        return `<rb>${kanji}</rb><rt>${readings.join("")}</rt>`;
    }
}

function ajt__reformat_multi_furigana() {
    const separators = /[\s;,.、・。]+/iu;
    const max_inline = 2;
    document.querySelectorAll("ruby:not(ruby ruby)").forEach((ruby) => {
        try {
            const kanji = (ruby.querySelector("rb") || ruby.firstChild).textContent.trim();
            const readings = ruby
                .querySelector("rt")
                .textContent.split(separators)
                .map((str) => str.trim())
                .filter((str) => str.length);

            if (readings.length > 1) {
                ruby.innerHTML = ajt__format_new_ruby(kanji, readings.slice(0, max_inline));
            }
            if (readings.length > max_inline) {
                const sequence = readings
                    .map((reading) => `<span class="ajt__tooltip-reading">${reading}</span>`)
                    .join("");
                const wrapper = document.createElement("span");
                wrapper.classList.add("ajt__tooltip");
                wrapper.insertAdjacentHTML("beforeend", `<span class="ajt__tooltip-text">${sequence}</span>`);
                ruby.replaceWith(wrapper);
                wrapper.appendChild(ruby);
            }
        } catch (error) {
            console.error(error);
        }
    });
}

function ajt__make_accents_list(ajt_span) {
    const accents = document.createElement("ul");
    for (const accent of ajt_span.getAttribute("pitch").split(" ")) {
        const [kana, pitch_type, pitch_num] = accent.split(/[-:]/g);
        const pattern = ajt__make_pattern(kana, pitch_type, pitch_num);
        accents.insertAdjacentHTML("beforeend", `<li><span class="ajt__downstep_${pitch_type}">${pattern}</span></li>`);
    }
    return accents;
}

function ajt__popup_cleanup() {
    for (const popup_elem of document.querySelectorAll(".ajt__info_popup")) {
        popup_elem.remove();
    }
}

function ajt__adjust_popup_position(popup_div) {
    const elem_rect = popup_div.getBoundingClientRect();
    const right_corner_x = elem_rect.x + elem_rect.width;
    const overflow_x = right_corner_x - window.innerWidth;
    /* By default the left property is set to 50% */
    if (elem_rect.x < 0) {
        popup_div.style.left = `calc(50% + ${-elem_rect.x}px + 0.5rem)`;
    } else if (overflow_x > 0) {
        popup_div.style.left = `calc(50% - ${overflow_x}px - 0.5rem)`;
    } else {
        popup_div.style.left = void 0;
    }
}

function ajt__make_popup_div(content) {
    /* Popup Top frame */
    const frame_top = document.createElement("div");
    frame_top.classList.add("ajt__frame_top");
    frame_top.innerHTML = `<span>Information</span>`;

    /* Popup Content */
    const frame_bottom = document.createElement("div");
    frame_bottom.classList.add("ajt__frame_bottom");
    frame_bottom.appendChild(content);

    /* Make Popup */
    const popup = document.createElement("div");
    popup.classList.add("ajt__info_popup");
    popup.appendChild(frame_top);
    popup.appendChild(frame_bottom);
    return popup;
}

function ajt__create_popups() {
    for (const [idx, span] of document.querySelectorAll(".ajt__word_info").entries()) {
        if (span.matches(".jpsentence .background *")) {
            /* fix for "Japanese sentences" note type */
            continue;
        }
        const content_ul = ajt__make_accents_list(span);
        const popup = ajt__make_popup_div(content_ul);
        popup.setAttribute("ajt__popup_idx", idx);
        span.setAttribute("ajt__popup_idx", idx);
        span.appendChild(popup);
        ajt__adjust_popup_position(popup);
    }
}

/* Setup */
ajt__popup_cleanup();
ajt__create_popups();
ajt__reformat_multi_furigana();
