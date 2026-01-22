"""GUI interface for AI File Organizer."""

import threading

import PySimpleGUI as sg

from .organizer import FileOrganizer


def main():
    """Main GUI entry point."""
    sg.theme("DarkBlue3")

    # Define the layout
    layout = [
        [sg.Text("AI File Organizer", font=("Helvetica", 20))],
        [sg.HorizontalSeparator()],
        [
            sg.Text("Input Folder:", size=(15, 1)),
            sg.Input(key="input_folder", size=(40, 1)),
            sg.FolderBrowse(),
        ],
        [
            sg.Text("Output Folder:", size=(15, 1)),
            sg.Input(key="output_folder", size=(40, 1)),
            sg.FolderBrowse(),
        ],
        [sg.HorizontalSeparator()],
        [sg.Text("Labels (comma-separated):", size=(20, 1))],
        [
            sg.Input(
                key="labels",
                size=(55, 1),
                default_text="Documents, Images, Videos, Audio, Archives, Code, Other",
            )
        ],
        [sg.HorizontalSeparator()],
        [sg.Text("LLM Configuration", font=("Helvetica", 14))],
        [
            sg.Text("Provider:", size=(15, 1)),
            sg.Combo(
                ["openai", "azure", "google", "local"],
                default_value="openai",
                key="provider",
                size=(20, 1),
            ),
        ],
        [
            sg.Text("Model:", size=(15, 1)),
            sg.Input(key="model", default_text="gpt-3.5-turbo", size=(20, 1)),
        ],
        [
            sg.Text("API Key:", size=(15, 1)),
            sg.Input(key="api_key", password_char="*", size=(40, 1)),
        ],
        [
            sg.Text("Temperature:", size=(15, 1)),
            sg.Slider(
                range=(0.0, 1.0),
                default_value=0.3,
                resolution=0.1,
                orientation="h",
                key="temperature",
                size=(30, 15),
            ),
        ],
        [
            sg.Checkbox(
                "Dry Run (don't actually move files)", key="dry_run", default=False
            )
        ],
        [sg.HorizontalSeparator()],
        [
            sg.Button("Start Organizing", size=(15, 1)),
            sg.Button("Cancel", size=(15, 1)),
        ],
        [sg.HorizontalSeparator()],
        [sg.Text("Progress:", font=("Helvetica", 12))],
        [sg.Multiline(size=(70, 10), key="output", autoscroll=True, disabled=True)],
        [sg.ProgressBar(100, orientation="h", size=(60, 20), key="progress")],
    ]

    # Create the window
    window = sg.Window("AI File Organizer", layout, finalize=True)

    # Event loop
    while True:
        event, values = window.read(timeout=100)

        if event == sg.WIN_CLOSED or event == "Cancel":
            break

        if event == "Start Organizing":
            # Validate inputs
            if not values["input_folder"]:
                sg.popup_error("Please select an input folder")
                continue

            if not values["output_folder"]:
                sg.popup_error("Please select an output folder")
                continue

            if not values["labels"]:
                sg.popup_error("Please specify labels")
                continue

            if not values["api_key"] and values["provider"] != "local":
                sg.popup_error("Please provide an API key")
                continue

            # Parse labels
            labels = [label.strip() for label in values["labels"].split(",")]

            # Build AI config
            ai_config = {
                "provider": values["provider"],
                "model": values["model"],
                "temperature": values["temperature"],
                "api_key": values["api_key"] if values["api_key"] else None,
            }

            # Disable the start button
            window["Start Organizing"].update(disabled=True)
            window["output"].update("")
            window["progress"].update(0)

            def organize_files_thread():
                """Thread function to organize files."""
                try:
                    organizer = FileOrganizer(ai_config, labels)

                    window["output"].print("Starting file organization...")
                    window["output"].print(f'Input folder: {values["input_folder"]}')
                    window["output"].print(f'Output folder: {values["output_folder"]}')
                    window["output"].print(f'Labels: {", ".join(labels)}')
                    window["output"].print(f'Provider: {ai_config["provider"]}')
                    window["output"].print(f'Model: {ai_config["model"]}')

                    if values["dry_run"]:
                        window["output"].print(
                            "\n*** DRY RUN MODE - No files will be moved ***\n"
                        )

                    stats = organizer.organize_files(
                        values["input_folder"],
                        values["output_folder"],
                        dry_run=values["dry_run"],
                    )

                    window["progress"].update(100)
                    window["output"].print("\n" + "=" * 50)
                    window["output"].print("Organization Complete!")
                    window["output"].print("=" * 50)
                    window["output"].print(f'Total files: {stats["total_files"]}')
                    window["output"].print(f'Processed: {stats["processed"]}')
                    window["output"].print(f'Failed: {stats["failed"]}')
                    window["output"].print("\nCategorization:")
                    for label, count in stats["categorization"].items():
                        window["output"].print(f"  {label}: {count} files")

                    sg.popup("File organization complete!", title="Success")

                except Exception as e:
                    window["output"].print(f"\nError: {str(e)}")
                    sg.popup_error(f"Error: {str(e)}")

                finally:
                    window["Start Organizing"].update(disabled=False)

            # Start organizing in a separate thread
            thread = threading.Thread(target=organize_files_thread, daemon=True)
            thread.start()

    window.close()


if __name__ == "__main__":
    main()
