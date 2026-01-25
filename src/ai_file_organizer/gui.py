"""GUI interface for AI File Organizer."""

import logging
import threading
from typing import Optional

import FreeSimpleGUI as sg
import yaml

from .organizer import FileOrganizer

logger = logging.getLogger(__name__)


class GuiLogHandler(logging.Handler):
    """Logging handler that sends formatted log records to the GUI main loop via write_event_value.

    It is safe to call from background threads because write_event_value is thread-safe.
    The main GUI loop listens for the "__LOG__" event and writes the payload into the GUI text widgets.
    """

    def __init__(self, window: sg.Window, event_key: str = "__LOG__") -> None:
        super().__init__()
        self._window = window
        self._event_key = event_key
        self.setLevel(logging.DEBUG)

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - GUI bridging
        try:
            msg = self.format(record)
            # Use write_event_value to safely queue an event for the main GUI thread
            try:
                self._window.write_event_value(self._event_key, msg)
            except Exception:
                # If window is closed / unavailable, ignore
                pass
        except Exception:
            self.handleError(record)


class OrganizeFileThread:
    """Thread class to organize files using FileOrganizer."""

    def __init__(
        self,
        ai_config: dict,
        labels: list,
        input_folder: str,
        output_folder: str,
        dry_run: bool,
        csv_report_path: Optional[str],
        window: sg.Window,
    ):
        self.ai_config = ai_config
        self.labels = labels
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.dry_run = dry_run
        self.csv_report_path = csv_report_path
        self.window = window

    def run(self):
        """Thread function to organize files. Use logging for messages and write a done event when finished."""
        try:
            logger.info("Starting file organization...")
            logger.info("Input folder: %s", self.input_folder)
            logger.info("Output folder: %s", self.output_folder)
            logger.info("Labels: %s", ", ".join(self.labels))
            logger.info("Provider: %s", self.ai_config["provider"])
            logger.info("Model: %s", self.ai_config["model"])

            if self.dry_run:
                logger.info("*** DRY RUN MODE - No files will be moved ***")

            organizer = FileOrganizer(
                self.ai_config,
                self.labels,
                self.input_folder,
                self.output_folder,
                dry_run=self.dry_run,
                csv_report_path=self.csv_report_path,
            )

            stats = organizer.organize_files()

            # Send done event with stats so main loop can update UI in the main thread
            try:
                self.window.write_event_value("__ORG_DONE__", stats)
            except Exception:
                # Fallback: log the completion
                logger.info("Organization finished: %s", stats)

        except Exception as e:
            logging.getLogger(__name__).exception("Error during organization: %s", e)
            try:
                self.window.write_event_value("__ORG_DONE__", {"total_files": 0, "processed": 0, "failed": 1, "categorization": {}})
            except Exception:
                pass


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
        [sg.Checkbox("Dry Run (don't actually move files)", key="dry_run", default=False)],
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
    window = sg.Window("AI File Organizer", layout, size=(900, 700), resizable=True, finalize=True)

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
        labels_list = [label.strip() for label in labels_raw.split(",") if label.strip()]

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

    # Keep reference to optional log window and handler
    log_handler: Optional[logging.Handler] = None

    # Event loop - use read_all_windows so we can handle the log window and events from worker threads
    while True:
        # read_all_windows returns (window, event, values)
        win, event, values = sg.read_all_windows(timeout=100)

        # If no window is active (timed out), continue
        if win is None:
            continue

        if win != window:
            continue

        # Handle log events sent from the logging handler (background threads)
        if event == "__LOG__":
            msg = values.get("__LOG__")
            if msg is not None:
                try:
                    # Append to main output area
                    window["output"].print(msg)
                except Exception:
                    pass
            continue

        # Handle organizer-done event
        if event == "__ORG_DONE__":
            stats = values.get("__ORG_DONE__")
            # Remove handler if present
            if log_handler is not None:
                try:
                    logging.getLogger().removeHandler(log_handler)
                except Exception:
                    pass
                log_handler = None

            # Update UI: re-enable Start button and show stats in main output
            try:
                window["Start Organizing"].update(disabled=False)
            except Exception:
                pass

            if isinstance(stats, dict):
                try:
                    window["progress"].update(100)
                except Exception:
                    pass
                try:
                    window["output"].print("\n" + "=" * 50)
                    window["output"].print("Organization Complete!")
                    window["output"].print("=" * 50)
                    window["output"].print(f'Total files: {stats.get("total_files")}')
                    window["output"].print(f'Processed: {stats.get("processed")}')
                    window["output"].print(f'Failed: {stats.get("failed")}')
                    window["output"].print("\nCategorization:")
                    for label, count in stats.get("categorization", {}).items():
                        window["output"].print(f"  {label}: {count} files")
                except Exception:
                    pass

            # Keep the log window open for user to inspect; user can close it manually
            continue

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

            # Attach logging handler to root logger so all logs are visible
            if log_handler is None:
                log_handler = GuiLogHandler(window)
                formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
                log_handler.setFormatter(formatter)
                logging.getLogger().addHandler(log_handler)

            thread = OrganizeFileThread(
                ai_config=ai_config,
                labels=labels,
                input_folder=values["input_folder"],
                output_folder=values["output_folder"],
                dry_run=values["dry_run"],
                csv_report_path=values.get("csv_report"),
                window=window,
            )

            # Start organizing in a separate thread
            thread = threading.Thread(target=thread.run, daemon=True)
            thread.start()

    # End event loop
    # Close any remaining windows
    window.close()


if __name__ == "__main__":
    main()
