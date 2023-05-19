import argparse
import os

import gradio as gr
import numpy as np
import yaml

from samtool.sammer import Sammer


def create_demo(imagedir: str, labeldir: str, annotations: str):
    with gr.Blocks() as demo:

        all_images = [f for f in imagedir]
        all_labels = yaml.safe_load(open(annotations))

        sam = Sammer(
            all_labels,
            imagedir,
            labeldir,
        )

        """BUILD INTERFACE"""
        # annotation tools
        with gr.Row():
            with gr.Column(scale=1):
                dropdown_filename = gr.Dropdown(all_images, label="File Selection")
                progress = gr.Textbox(show_label=False, interactive=False)

            radio_label = gr.Radio(
                choices=list(all_labels.keys()),
                value=list(all_labels.keys())[0],
                label="Label",
            )
            checkbox_validity = gr.Checkbox(value=True, label="Validity")

            with gr.Column(scale=2):
                # next and previous
                with gr.Row():
                    button_prev_unlabelled = gr.Button(
                        value="Prev Unlabelled", variant="primary"
                    )
                    button_prev = gr.Button(value="Previous", variant="secondary")
                    button_next = gr.Button(value="Next", variant="secondary")
                    button_next_unlabelled = gr.Button(
                        value="Next Unlabelled", variant="primary"
                    )

                with gr.Row():
                    button_reset_selection = gr.Button(
                        value="Reset Selection", variant="secondary"
                    )
                    button_reset_label = gr.Button(
                        value="Reset Label", variant="secondary"
                    )
                    button_reset_all = gr.Button(value="Reset All", variant="secondary")

        with gr.Row():
            # the display for annotation
            display_partial = gr.Image(interactive=False, show_label=False)

            # the display for everything
            display_complete = gr.Image(interactive=False, label="Complete Annotation")

        # approve the selection
        button_approve = gr.Button(value="Approve", variant="primary")

        """DEFINE INTERFACE FUNCTIONALITY"""

        def surrogate_reset(filename):
            done_labels = len(os.listdir(labeldir))
            progress_string = f"{done_labels} of {len(all_images)} completed."
            return *sam.reset(filename), progress_string

        # filename change
        dropdown_filename.change(
            fn=surrogate_reset,
            inputs=dropdown_filename,
            outputs=[display_partial, display_complete, progress],
        )

        # next file previous file
        def file_increment(ascend: bool, unlabelled_only: bool, filename: str):
            try:
                index = all_images.index(filename)
            except ValueError:
                index = 0

            while True:
                index += 1 if ascend else -1

                # don't exceed index
                if index <= -1 or index >= len(all_images):
                    index += 1 if not ascend else -1
                    break

                # we don't care if labelled of unlabelled
                if not unlabelled_only:
                    break

                # we only care if unlabelled
                maskfile = os.path.join(labeldir, f"{all_images[index]}.npy")
                if not os.path.isfile(maskfile):
                    break

            return all_images[index]

        button_prev_unlabelled.click(
            fn=lambda f: file_increment(ascend=False, unlabelled_only=True, filename=f),
            inputs=dropdown_filename,
            outputs=dropdown_filename,
        )
        button_prev.click(
            fn=lambda f: file_increment(
                ascend=False, unlabelled_only=False, filename=f
            ),
            inputs=dropdown_filename,
            outputs=dropdown_filename,
        )
        button_next.click(
            fn=lambda f: file_increment(ascend=True, unlabelled_only=False, filename=f),
            inputs=dropdown_filename,
            outputs=dropdown_filename,
        )
        button_next_unlabelled.click(
            fn=lambda f: file_increment(ascend=True, unlabelled_only=True, filename=f),
            inputs=dropdown_filename,
            outputs=dropdown_filename,
        )

        # clear the selection image
        button_reset_selection.click(
            fn=sam.clear_coords_validity, outputs=display_partial
        )
        # clear only the labels in the complete image
        button_reset_label.click(
            fn=lambda f, l: sam.clear_comp_mask(filename=f, label=l),
            inputs=[dropdown_filename, radio_label],
            outputs=[display_partial, display_complete],
        )
        # clear everything
        button_reset_all.click(
            fn=lambda f: sam.clear_comp_mask(filename=f, label=None),
            inputs=dropdown_filename,
            outputs=[display_partial, display_complete],
        )

        # gather clicks
        def update_prediction(event: gr.SelectData, validity, label):
            sam.add_coords_validity(np.array(event.index), validity)
            return sam.update_part_image(label)

        display_partial.select(
            fn=update_prediction,
            inputs=[checkbox_validity, radio_label],
            outputs=display_partial,
        )

        # approve the segmentation to be a mask
        button_approve.click(
            fn=sam.part_to_comp_mask,
            inputs=[dropdown_filename, radio_label],
            outputs=[display_partial, display_complete],
        )

    return demo


def main():
    parser = argparse.ArgumentParser(
        prog="SAMTool",
        description="Semantic Segmentation Dataset Creation Tool powered by Segment Anything Model from Meta.",
    )
    parser.add_argument("--imagedir", required=True)
    parser.add_argument("--labeldir", required=True)
    parser.add_argument("--annotations", required=True)
    args = parser.parse_args()

    create_demo(args.imagedir, args.labeldir, args.annotations).launch()
