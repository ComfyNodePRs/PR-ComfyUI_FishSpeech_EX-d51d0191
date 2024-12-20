from typing import Callable

import gradio as gr

from fish_speech.i18n import i18n
from tools.inference_engine.utils import normalize_text
from tools.webui.variables import HEADER_MD, TEXTBOX_PLACEHOLDER


def build_app(inference_fct: Callable, theme: str = "light") -> gr.Blocks:
    with gr.Blocks(theme=gr.themes.Base()) as app:
        gr.Markdown(HEADER_MD)

        # Use light theme by default
        app.load(
            None,
            None,
            js="() => {const params = new URLSearchParams(window.location.search);if (!params.has('__theme')) {params.set('__theme', '%s');window.location.search = params.toString();}}"
            % theme,
        )

        # Inference
        with gr.Row():
            with gr.Column(scale=3):
                text = gr.Textbox(
                    label=i18n("Input Text"), placeholder=TEXTBOX_PLACEHOLDER, lines=10
                )
                refined_text = gr.Textbox(
                    label=i18n("Realtime Transform Text"),
                    placeholder=i18n(
                        "Normalization Result Preview (Currently Only Chinese)"
                    ),
                    lines=5,
                    interactive=False,
                )

                with gr.Row():
                    normalize = gr.Checkbox(
                        label=i18n("Text Normalization"),
                        value=False,
                    )

                with gr.Row():
                    with gr.Column():
                        with gr.Tab(label=i18n("Reference Audio")):
                            with gr.Row():
                                gr.Markdown(
                                    i18n(
                                        "5 to 10 seconds of reference audio, useful for specifying speaker."
                                    )
                                )
                            with gr.Row():
                                reference_id = gr.Textbox(
                                    label=i18n("Reference ID"),
                                    placeholder=i18n("Leave empty to use uploaded references"),
                                )

                            with gr.Row():
                                use_memory_cache = gr.Radio(
                                    label=i18n("Use Memory Cache"),
                                    choices=[i18n("on"), i18n("off")],
                                    value=i18n("on"),
                                )

                            with gr.Row():
                                from pathlib import Path
                                initial_audio_files = [str(p) for p in Path("references").glob("**/*") if p.suffix.lower() in [".wav", ".mp3", ".flac"]]
                                example_audio_dropdown = gr.Dropdown(
                                    label=i18n("Select Example Audio"),
                                    choices=initial_audio_files + [""],
                                    value="",
                                    interactive=True,
                                    allow_custom_value=True,
                                )
                                refresh_button = gr.Button(
                                    value="\U0001F504 刷新",
                                )

                            with gr.Row():
                                reference_audio = gr.Audio(
                                    label=i18n("Reference Audio"),
                                    type="filepath",
                                )
                            with gr.Row():
                                reference_text = gr.Textbox(
                                    label=i18n("Reference Text"),
                                    lines=1,
                                    placeholder="在一无所知中，梦里的一天结束了，一个新的「轮回」便会开始。",
                                    value="",
                                )

                        with gr.Tab(label=i18n("Advanced Config")):
                            with gr.Row():
                                chunk_length = gr.Slider(
                                    label=i18n("Iterative Prompt Length, 0 means off"),
                                    minimum=0,
                                    maximum=300,
                                    value=200,
                                    step=8,
                                )

                                max_new_tokens = gr.Slider(
                                    label=i18n(
                                        "Maximum tokens per batch, 0 means no limit"
                                    ),
                                    minimum=0,
                                    maximum=2048,
                                    value=0,
                                    step=8,
                                )

                            with gr.Row():
                                top_p = gr.Slider(
                                    label="Top-P",
                                    minimum=0.6,
                                    maximum=0.9,
                                    value=0.7,
                                    step=0.01,
                                )

                                repetition_penalty = gr.Slider(
                                    label=i18n("Repetition Penalty"),
                                    minimum=1,
                                    maximum=1.5,
                                    value=1.2,
                                    step=0.01,
                                )

                            with gr.Row():
                                temperature = gr.Slider(
                                    label=i18n("Temperature"),
                                    minimum=0.6,
                                    maximum=0.9,
                                    value=0.7,
                                    step=0.01,
                                )
                                seed = gr.Number(
                                    label=i18n("Seed"),
                                    info=i18n("0 means randomized inference, otherwise deterministic"),
                                    value=0,
                                )

            with gr.Column(scale=3):
                with gr.Row():
                    error = gr.HTML(
                        label=i18n("Error Message"),
                        visible=True,
                    )
                with gr.Row():
                    audio = gr.Audio(
                        label=i18n("Generated Audio"),
                        type="numpy",
                        interactive=False,
                        visible=True,
                    )

                with gr.Row():
                    used_seed = gr.Textbox(
                        label=i18n("Used Seed"),
                        value="",
                        interactive=False,
                    )

                with gr.Row():
                    with gr.Column(scale=3):
                        generate = gr.Button(
                            value="\U0001F3A7 " + i18n("Generate"),
                            variant="primary",
                        )

        text.input(fn=normalize_text, inputs=[text, normalize], outputs=[refined_text])

        # Refresh audio files list and update dropdown
        def refresh_audio_files():
            audio_files = [str(p) for p in Path("references").glob("**/*") if p.suffix.lower() in [".wav", ".mp3", ".flac"]]
            return gr.Dropdown(choices=audio_files + [""])

        refresh_button.click(
            fn=refresh_audio_files,
            inputs=[],
            outputs=[example_audio_dropdown],
        )

        # Update reference audio and text when dropdown changes
        def update_reference_audio_and_text(audio_path):
            if audio_path and audio_path != "":
                # Extract filename without extension as reference text
                reference_text = Path(audio_path).stem
                return audio_path, reference_text
            return None, ""
            
        example_audio_dropdown.change(
            fn=update_reference_audio_and_text,
            inputs=[example_audio_dropdown],
            outputs=[reference_audio, reference_text],
        )

        # Submit
        def preprocess_inputs(refined_text, normalize, reference_id, reference_audio, reference_text,
                            max_new_tokens, chunk_length, top_p, repetition_penalty, temperature,
                            seed, use_memory_cache):
            # Convert localized value back to English
            if use_memory_cache == i18n("on"):
                use_memory_cache = "on"
            else:
                use_memory_cache = "off"
            return [refined_text, normalize, reference_id, reference_audio, reference_text,
                   max_new_tokens, chunk_length, top_p, repetition_penalty, temperature,
                   seed, use_memory_cache]

        generate.click(
            lambda *args: inference_fct(*preprocess_inputs(*args)),
            [
                refined_text,
                normalize,
                reference_id,
                reference_audio,
                reference_text,
                max_new_tokens,
                chunk_length,
                top_p,
                repetition_penalty,
                temperature,
                seed,
                use_memory_cache,
            ],
            [audio, error, used_seed],
            concurrency_limit=1,
        )

    return app