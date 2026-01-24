"""GUI interface for AI File Organizer."""

import threading

import PySimpleGUI as sg
import yaml

from .organizer import FileOrganizer


def main():  # noqa: C901
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
        # CSV report selection (optional)
        [
            sg.Text("CSV Report (optional):", size=(15, 1)),
            sg.Input(key="csv_report", size=(40, 1)),
            sg.FileSaveAs(
                file_types=(("CSV Files", ("*.csv",)), ("All Files", "*.*")),
                default_extension=".csv",
            ),
        ],
        [sg.HorizontalSeparator()],
        [
            sg.Button("Start Organizing", size=(15, 1)),
            sg.Button("Cancel", size=(15, 1)),
            # Buttons to save/load configuration in the same YAML format as the CLI
            sg.Button("Save Config", size=(12, 1)),
            sg.Button("Load Config", size=(12, 1)),
        ],
        [sg.HorizontalSeparator()],
        [sg.Text("Progress:", font=("Helvetica", 12))],
        # Put the log and progress bar inside a Column that expands with the window
        [
            sg.Column(
                [
                    [
                        sg.Multiline(
                            size=(70, 10),
                            key="output",
                            autoscroll=True,
                            disabled=True,
                            expand_x=True,
                            expand_y=True,
                        )
                    ],
                    [
                        sg.ProgressBar(
                            100,
                            orientation="h",
                            size=(60, 20),
                            key="progress",
                            expand_x=True,
                        )
                    ],
                ],
                expand_x=True,
                expand_y=True,
                pad=(0, 0),
                key="-BOTTOM-",
            )
        ],
    ]

    # Create the window (make it larger and resizable)
    window = sg.Window(
        "AI File Organizer", layout, size=(900, 700), resizable=True, finalize=True
    )

    def _build_config_from_values(values: dict) -> dict:
        """Build a CLI-compatible YAML config dict from current GUI values."""
        # Build ai config
        ai = {
            "provider": values.get("provider", "openai"),
            "model": values.get("model", "gpt-3.5-turbo"),
            "temperature": float(values.get("temperature", 0.3)),
        }
        if values.get("api_key"):
            ai["api_key"] = values.get("api_key")

        # Labels: split comma-separated string into a list
        labels_raw = values.get("labels", "")
        labels_list = [
            label.strip() for label in labels_raw.split(",") if label.strip()
        ]

        cfg = {
            "ai": ai,
            "labels": labels_list,
        }

        # Optional folders
        if values.get("input_folder"):
            cfg["input_folder"] = values.get("input_folder")
        if values.get("output_folder"):
            cfg["output_folder"] = values.get("output_folder")
        if values.get("dry_run"):
            cfg["dry_run"] = values.get("dry_run")
        # Optional csv report path
        if values.get("csv_report"):
            cfg["csv_report"] = values.get("csv_report")

        return cfg

    def _apply_config_to_window(config: dict):
        """Apply a loaded CLI-compatible config dict to the GUI elements."""
        ai = config.get("ai", {}) or {}
        provider = ai.get("provider")
        model = ai.get("model")
        temperature = ai.get("temperature")
        api_key = ai.get("api_key")

        # Update AI-related fields
        if provider is not None:
            try:
                window["provider"].update(value=provider)
            except Exception:
                pass
        if model is not None:
            window["model"].update(value=model)
        if temperature is not None:
            try:
                window["temperature"].update(value=float(temperature))
            except Exception:
                pass
        if api_key is not None:
            window["api_key"].update(value=api_key)

        # Labels: can be a list or a dict (hierarchical). Convert to comma-separated top-level keys.
        labels = config.get("labels")
        if isinstance(labels, dict):
            # Use top-level keys as labels
            labels_str = ", ".join(labels.keys())
            window["labels"].update(value=labels_str)
        elif isinstance(labels, list):
            window["labels"].update(value=", ".join([str(x) for x in labels]))

        # Folders
        if config.get("input_folder"):
            window["input_folder"].update(value=config.get("input_folder"))
        if config.get("output_folder"):
            window["output_folder"].update(value=config.get("output_folder"))
        # CSV report path
        if config.get("csv_report"):
            window["csv_report"].update(value=config.get("csv_report"))

    # Event loop
    while True:
        event, values = window.read(timeout=100)

        if event == sg.WIN_CLOSED or event == "Cancel":
            break

        if event == "Save Config":
            # Ask for file path to save
            save_path = sg.popup_get_file(
                "Save configuration as...",
                save_as=True,
                file_types=(("YAML Files", ("*.yml", "*.yaml")), ("All Files", "*.*")),
                default_extension=".yml",
            )
            if save_path:
                # Ensure extension
                if not save_path.lower().endswith((".yml", ".yaml")):
                    save_path = save_path + ".yml"
                try:
                    cfg = _build_config_from_values(values)
                    with open(save_path, "w", encoding="utf-8") as f:
                        yaml.safe_dump(cfg, f, sort_keys=False)
                    sg.popup("Configuration saved", title="Success")
                except Exception as e:
                    sg.popup_error(f"Failed to save configuration: {e}")

        if event == "Load Config":
            load_path = sg.popup_get_file(
                "Load configuration file...",
                file_types=(("YAML Files", ("*.yml", "*.yaml")), ("All Files", "*.*")),
            )
            if load_path:
                try:
                    with open(load_path, "r", encoding="utf-8") as f:
                        cfg = yaml.safe_load(f) or {}
                    _apply_config_to_window(cfg)
                    sg.popup("Configuration loaded", title="Success")
                except Exception as e:
                    sg.popup_error(f"Failed to load configuration: {e}")

        if event == "Start Organizing":
            # Validate inputs
            if not values["input_folder"]:
                sg.popup_error("Please select an input folder")
                continue

            if (not values["dry_run"]) and not values["output_folder"]:
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
                    organizer = FileOrganizer(
                        ai_config,
                        labels,
                        values["input_folder"],
                        values["output_folder"],
                        dry_run=values["dry_run"],
                        csv_report_path=values.get("csv_report"),
                    )

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

                    stats = organizer.organize_files()

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
