"""
author/window.py

Author tool — main window.

Slice 1: full stub layout. Vocabulary-driven section headers.
         Multi-select support technique assignment in properties panel.

Slice 2: video loading, frame scrubber, annotation workflow.
Slice 3: flow builder panel.
Slice 4: publish + document preview.
"""

from __future__ import annotations

from pathlib import Path
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QFrame,
    QTabWidget, QTextEdit, QToolBar, QStatusBar, QMessageBox,
    QFileDialog, QGroupBox,
)

from normaformae.core.discipline_loader import (
    load_discipline, load_all_stances, load_all_sequences,
    load_all_flows, load_all_support_techniques, get_vocabulary,
    save_support_technique, DisciplineLoadError,
)
from normaformae.glossary import UI


class AuthorWindow(QMainWindow):
    """
    Main window for the Author persona.

    Layout (left → right):
        [Catalog panel]  |  [Work area — tabs]  |  [Properties panel]

    Support techniques are shown as a multi-select checklist in the
    properties panel, between Beschreibung and Häufige Fehler.
    Any number of support techniques can be assigned to one item.
    Assignments are saved immediately to the support technique's
    referenced_by list.
    """

    def __init__(self, discipline_path: str) -> None:
        super().__init__()
        self._discipline_path = discipline_path
        self._discipline: dict = {}
        self._vocab: dict = {}
        self._stances: dict = {}
        self._sequences: dict = {}
        self._flows: dict = {}
        self._support: dict = {}

        # Track which item is currently shown in the properties panel
        self._current_item_id: str = ""
        self._current_item_type: str = ""  # "stance" | "sequence" | "flow" | "support"

        self.setWindowTitle(UI["author_window_title"])
        self.setMinimumSize(1100, 700)

        self._load_discipline_data()
        self._build_toolbar()
        self._build_ui()
        self._build_statusbar()
        self._populate_catalog()

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_discipline_data(self) -> None:
        try:
            self._discipline = load_discipline(self._discipline_path)
            self._vocab      = get_vocabulary(self._discipline)
            self._stances    = load_all_stances(self._discipline_path)
            self._sequences  = load_all_sequences(self._discipline_path)
            self._flows      = load_all_flows(self._discipline_path)
            self._support    = load_all_support_techniques(self._discipline_path)
        except DisciplineLoadError as e:
            QMessageBox.critical(self, "Fehler", str(e))

    # ------------------------------------------------------------------
    # Toolbar
    # ------------------------------------------------------------------

    def _build_toolbar(self) -> None:
        tb = QToolBar("Hauptwerkzeugleiste")
        tb.setMovable(False)
        self.addToolBar(tb)

        self._act_load_video = tb.addAction(UI["load_video"])
        self._act_load_video.triggered.connect(self._on_load_video)
        tb.addSeparator()

        self._act_new_flow = tb.addAction(UI["new_flow"])
        self._act_new_flow.triggered.connect(self._on_new_flow)

        self._act_open_flow = tb.addAction(UI["open_flow"])
        self._act_open_flow.triggered.connect(self._on_open_flow)

        self._act_save_draft = tb.addAction(UI["save_draft"])
        self._act_save_draft.triggered.connect(self._on_save_draft)

        self._act_publish = tb.addAction(UI["publish_flow"])
        self._act_publish.triggered.connect(self._on_publish)

        tb.addSeparator()
        disc_name = self._discipline.get("display_name", self._discipline_path)
        tb.addWidget(QLabel(f"  {disc_name}  "))

    # ------------------------------------------------------------------
    # Main UI layout
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        splitter.addWidget(self._build_catalog_panel())
        splitter.addWidget(self._build_work_area())
        splitter.addWidget(self._build_properties_panel())
        splitter.setSizes([242, 594, 264])

    # ------------------------------------------------------------------
    # Left: Catalog panel
    # ------------------------------------------------------------------

    def _build_catalog_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(200)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel("Katalog")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)

        static_box = QGroupBox(self._vocab["static"]["plural"])
        static_layout = QVBoxLayout(static_box)
        self._stance_list = QListWidget()
        self._stance_list.setMaximumHeight(160)
        self._stance_list.itemClicked.connect(self._on_stance_selected)
        static_layout.addWidget(self._stance_list)
        layout.addWidget(static_box)

        trans_box = QGroupBox(self._vocab["transition"]["plural"])
        trans_layout = QVBoxLayout(trans_box)
        self._sequence_list = QListWidget()
        self._sequence_list.setMaximumHeight(120)
        self._sequence_list.itemClicked.connect(self._on_sequence_selected)
        trans_layout.addWidget(self._sequence_list)
        layout.addWidget(trans_box)

        flows_box = QGroupBox(self._vocab["flow"]["plural"])
        flows_layout = QVBoxLayout(flows_box)
        self._flow_list = QListWidget()
        self._flow_list.setMaximumHeight(100)
        self._flow_list.itemClicked.connect(self._on_flow_selected)
        flows_layout.addWidget(self._flow_list)
        layout.addWidget(flows_box)

        support_box = QGroupBox(self._vocab["support"]["plural"])
        support_layout = QVBoxLayout(support_box)
        self._support_list = QListWidget()
        self._support_list.itemClicked.connect(self._on_support_selected)
        support_layout.addWidget(self._support_list)
        layout.addWidget(support_box)

        return panel

    # ------------------------------------------------------------------
    # Centre: Work area
    # ------------------------------------------------------------------

    def _build_work_area(self) -> QWidget:
        self._work_tabs = QTabWidget()
        self._work_tabs.addTab(self._build_annotation_tab(), "Video & Annotation")
        self._work_tabs.addTab(
            self._build_flow_builder_tab(),
            self._vocab["flow"]["singular"] + "-Builder"
        )
        return self._work_tabs

    def _build_annotation_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        video_placeholder = QFrame()
        video_placeholder.setFrameShape(QFrame.Shape.Box)
        video_placeholder.setMinimumHeight(320)
        video_placeholder.setStyleSheet(
            "background-color: #1a1a1a; border: 1px solid #444;"
        )
        placeholder_label = QLabel(
            "Video noch nicht geladen\n\n"
            f"→ '{UI['load_video']}' in der Werkzeugleiste"
        )
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("color: #888; font-size: 13px;")
        placeholder_layout = QVBoxLayout(video_placeholder)
        placeholder_layout.addWidget(placeholder_label)
        layout.addWidget(video_placeholder)

        scrubber_placeholder = QFrame()
        scrubber_placeholder.setFrameShape(QFrame.Shape.Box)
        scrubber_placeholder.setFixedHeight(48)
        scrubber_placeholder.setStyleSheet(
            "background-color: #2a2a2a; border: 1px solid #555;"
        )
        scrubber_label = QLabel("Zeitachse (Slice 2)")
        scrubber_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scrubber_label.setStyleSheet("color: #666; font-size: 11px;")
        scrubber_layout = QVBoxLayout(scrubber_placeholder)
        scrubber_layout.addWidget(scrubber_label)
        layout.addWidget(scrubber_placeholder)

        btn_row = QHBoxLayout()
        for label in (
            self._vocab["static"]["singular"],
            self._vocab["transition"]["singular"],
            self._discipline.get("annotation_labels", {}).get("ignore", "Ignorieren"),
        ):
            btn = QPushButton(label)
            btn.setMinimumHeight(36)
            btn.setEnabled(False)
            btn.setToolTip("Verfügbar nach dem Laden eines Videos (Slice 2)")
            btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        return tab

    def _build_flow_builder_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        info = QLabel(
            f"{self._vocab['flow']['plural']}-Builder (Slice 3)\n\n"
            "Hier werden annotierte Sequenzen per Drag-and-Drop\n"
            f"zu einem {self._vocab['flow']['singular']} zusammengestellt."
        )
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setStyleSheet("color: #888; font-size: 13px;")
        layout.addWidget(info)

        self._flow_builder_list = QListWidget()
        self._flow_builder_list.setEnabled(False)
        self._flow_builder_list.setToolTip("Verfügbar in Slice 3")
        layout.addWidget(self._flow_builder_list)

        return tab

    # ------------------------------------------------------------------
    # Right: Properties panel
    # ------------------------------------------------------------------

    def _build_properties_panel(self) -> QWidget:
        panel = QWidget()
        panel.setMinimumWidth(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header = QLabel("Eigenschaften")
        header.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(header)
        layout.addWidget(_divider())

        self._prop_name = QLabel("—")
        self._prop_name.setStyleSheet("font-size: 13px; font-weight: bold;")
        self._prop_name.setWordWrap(True)
        layout.addWidget(self._prop_name)

        self._prop_status = QLabel("")
        self._prop_status.setStyleSheet("font-size: 11px; color: gray;")
        layout.addWidget(self._prop_status)

        layout.addWidget(_divider())

        # Beschreibung
        layout.addWidget(_bold_label(UI["description_field"]))
        self._prop_description = QTextEdit()
        self._prop_description.setMaximumHeight(80)
        self._prop_description.setPlaceholderText("Beschreibung…")
        self._prop_description.setEnabled(False)
        layout.addWidget(self._prop_description)

        layout.addWidget(_divider())

        # Support techniques — multi-select checklist
        # Each entry has a checkbox. Checking/unchecking saves immediately.
        self._prop_support_label = _bold_label(self._vocab["support"]["plural"])
        layout.addWidget(self._prop_support_label)

        self._prop_support_hint = QLabel("Mehrfachauswahl möglich")
        self._prop_support_hint.setStyleSheet("font-size: 10px; color: gray;")
        layout.addWidget(self._prop_support_hint)

        self._prop_support_checklist = QListWidget()
        self._prop_support_checklist.setMaximumHeight(100)
        self._prop_support_checklist.setEnabled(False)
        self._prop_support_checklist.itemChanged.connect(
            self._on_support_assignment_changed
        )
        layout.addWidget(self._prop_support_checklist)

        layout.addWidget(_divider())

        # Häufige Fehler
        layout.addWidget(_bold_label(UI["common_errors_field"]))
        self._prop_errors = QTextEdit()
        self._prop_errors.setMaximumHeight(80)
        self._prop_errors.setPlaceholderText("Häufige Fehler (je Zeile ein Fehler)…")
        self._prop_errors.setEnabled(False)
        layout.addWidget(self._prop_errors)

        layout.addWidget(_divider())

        # Reference image + wiki
        layout.addWidget(_bold_label(UI["reference_image"]))
        ref_row = QHBoxLayout()
        self._prop_ref_img_label = QLabel(UI["no_reference_image"])
        self._prop_ref_img_label.setStyleSheet("font-size: 11px; color: gray;")
        self._prop_ref_img_label.setWordWrap(True)
        ref_row.addWidget(self._prop_ref_img_label)
        self._prop_ref_img_btn = QPushButton(UI["browse"])
        self._prop_ref_img_btn.setEnabled(False)
        ref_row.addWidget(self._prop_ref_img_btn)
        layout.addLayout(ref_row)

        self._btn_wiki = QPushButton(UI["search_wiki"])
        self._btn_wiki.setEnabled(False)
        self._btn_wiki.clicked.connect(self._on_search_wiki)
        layout.addWidget(self._btn_wiki)

        layout.addStretch()

        layout.addWidget(_divider())
        self._prop_frame_info = QLabel(UI["timestamp_auto"] + ": —")
        self._prop_frame_info.setStyleSheet("font-size: 10px; color: gray;")
        self._prop_frame_info.setWordWrap(True)
        layout.addWidget(self._prop_frame_info)

        return panel

    # ------------------------------------------------------------------
    # Status bar
    # ------------------------------------------------------------------

    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)
        disc_name = self._discipline.get("display_name", "")
        v = self._vocab
        sb.showMessage(
            f"{disc_name}  ·  "
            f"{len(self._stances)} {v['static']['plural']}  ·  "
            f"{len(self._sequences)} {v['transition']['plural']}  ·  "
            f"{len(self._flows)} {v['flow']['plural']}  ·  "
            f"{len(self._support)} {v['support']['plural']}"
        )

    # ------------------------------------------------------------------
    # Catalog population
    # ------------------------------------------------------------------

    def _populate_catalog(self) -> None:
        self._stance_list.clear()
        for sid, s in self._stances.items():
            has_frame = s.get("extracted_frame") is not None
            icon = "✓" if has_frame else "○"
            item = QListWidgetItem(f"{icon} {s['label']}")
            item.setData(Qt.ItemDataRole.UserRole, sid)
            if not has_frame:
                item.setForeground(Qt.GlobalColor.gray)
            self._stance_list.addItem(item)

        self._sequence_list.clear()
        for seq_id, seq in self._sequences.items():
            item = QListWidgetItem(seq.get("label", seq_id))
            item.setData(Qt.ItemDataRole.UserRole, seq_id)
            self._sequence_list.addItem(item)

        self._flow_list.clear()
        for fid, flow in self._flows.items():
            status = flow.get("status", "draft")
            icon = "▶" if status == "published" else "✎"
            item = QListWidgetItem(f"{icon} {flow.get('label', fid)}")
            item.setData(Qt.ItemDataRole.UserRole, fid)
            self._flow_list.addItem(item)

        self._support_list.clear()
        for tid, tech in self._support.items():
            status = tech.get("status", "draft")
            icon = "✓" if status == "published" else "○"
            item = QListWidgetItem(f"{icon} {tech.get('label', tid)}")
            item.setData(Qt.ItemDataRole.UserRole, tid)
            self._support_list.addItem(item)

    # ------------------------------------------------------------------
    # Support checklist — populate and handle changes
    # ------------------------------------------------------------------

    def _populate_support_checklist(self, item_id: str) -> None:
        """
        Fill the checklist with all available support techniques.
        Pre-check those whose referenced_by includes item_id.
        Temporarily block signals to avoid triggering saves during population.
        """
        self._prop_support_checklist.blockSignals(True)
        self._prop_support_checklist.clear()

        for tid, tech in self._support.items():
            refs = tech.get("referenced_by", [])
            checked = item_id in refs
            list_item = QListWidgetItem(tech.get("label", tid))
            list_item.setData(Qt.ItemDataRole.UserRole, tid)
            list_item.setFlags(
                list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable
            )
            list_item.setCheckState(
                Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
            )
            self._prop_support_checklist.addItem(list_item)

        self._prop_support_checklist.setEnabled(True)
        self._prop_support_checklist.blockSignals(False)

    def _on_support_assignment_changed(self, list_item: QListWidgetItem) -> None:
        """
        Called when a checkbox is toggled.
        Adds or removes the current item_id from the technique's referenced_by
        and saves the technique JSON immediately.
        """
        if not self._current_item_id:
            return

        technique_id = list_item.data(Qt.ItemDataRole.UserRole)
        tech = self._support.get(technique_id)
        if not tech:
            return

        item_id = self._current_item_id
        refs: list = list(tech.get("referenced_by", []))
        is_checked = list_item.checkState() == Qt.CheckState.Checked

        if is_checked and item_id not in refs:
            refs.append(item_id)
        elif not is_checked and item_id in refs:
            refs.remove(item_id)
        else:
            return  # no change

        tech["referenced_by"] = refs

        try:
            save_support_technique(self._discipline_path, tech)
            # Reload to keep in-memory state in sync
            self._support[technique_id] = tech
            self.statusBar().showMessage(
                f"{UI['file_saved']}: {tech.get('label', technique_id)}"
            )
        except Exception as e:
            QMessageBox.warning(self, "Fehler", f"Konnte nicht speichern: {e}")

    # ------------------------------------------------------------------
    # Toolbar actions
    # ------------------------------------------------------------------

    def _on_load_video(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, UI["load_video"], "",
            "Videodateien (*.mp4 *.mov *.avi *.mkv);;Alle Dateien (*)"
        )
        if path:
            self.statusBar().showMessage(
                f"Video ausgewählt: {Path(path).name}  "
                "[Slice 2: Verarbeitung noch nicht implementiert]"
            )

    def _on_new_flow(self) -> None:
        _stub_message(self, UI["new_flow"])

    def _on_open_flow(self) -> None:
        _stub_message(self, UI["open_flow"])

    def _on_save_draft(self) -> None:
        _stub_message(self, UI["save_draft"])

    def _on_publish(self) -> None:
        reply = QMessageBox.question(
            self, UI["publish_flow"], UI["confirm_publish"],
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            _stub_message(self, UI["publish_flow"])

    def _on_search_wiki(self) -> None:
        from PyQt6.QtGui import QDesktopServices
        from PyQt6.QtCore import QUrl
        term = self._prop_name.text().replace("—", "").strip()
        if not term:
            return
        base_url = self._discipline.get(
            "wiktenauer_search_url",
            "https://wiktenauer.com/wiki/Special:Search?search={term}"
        )
        QDesktopServices.openUrl(QUrl(base_url.replace("{term}", term)))

    # ------------------------------------------------------------------
    # Catalog selection handlers
    # ------------------------------------------------------------------

    def _on_stance_selected(self, item: QListWidgetItem) -> None:
        sid = item.data(Qt.ItemDataRole.UserRole)
        self._current_item_id   = sid
        self._current_item_type = "stance"
        stance = self._stances.get(sid, {})
        self._show_item_properties(
            label=stance.get("label", sid),
            status=stance.get("status", "draft"),
            description=stance.get("description", ""),
            errors=stance.get("common_errors", []),
            frame_info=_format_frame_info(stance),
            ref_image=stance.get("reference_image"),
            wiki_enabled=True,
            show_support_panel=True,
        )

    def _on_sequence_selected(self, item: QListWidgetItem) -> None:
        seq_id = item.data(Qt.ItemDataRole.UserRole)
        self._current_item_id   = seq_id
        self._current_item_type = "sequence"
        seq = self._sequences.get(seq_id, {})
        self._show_item_properties(
            label=seq.get("label", seq_id),
            status=seq.get("status", "draft"),
            description=seq.get("description", ""),
            errors=seq.get("common_errors", []),
            frame_info=f"Dauer: {seq.get('duration_seconds', '—')} s",
            show_support_panel=True,
        )

    def _on_flow_selected(self, item: QListWidgetItem) -> None:
        fid = item.data(Qt.ItemDataRole.UserRole)
        self._current_item_id   = fid
        self._current_item_type = "flow"
        flow = self._flows.get(fid, {})
        seq_count = len(flow.get("sequence_ids", []))
        self._show_item_properties(
            label=flow.get("label", fid),
            status=flow.get("status", "draft"),
            description=flow.get("description", ""),
            errors=[],
            frame_info=(
                f"Sequenzen: {seq_count}  ·  "
                f"Niveau: {flow.get('practitioner_level', '—')}"
            ),
            show_support_panel=False,
        )

    def _on_support_selected(self, item: QListWidgetItem) -> None:
        tid = item.data(Qt.ItemDataRole.UserRole)
        self._current_item_id   = tid
        self._current_item_type = "support"
        tech = self._support.get(tid, {})
        combined = tech.get("description", "")
        instruction = tech.get("instruction", "")
        if instruction:
            combined = combined + "\n\n" + instruction
        self._show_item_properties(
            label=tech.get("label", tid),
            status=tech.get("status", "draft"),
            description=combined,
            errors=tech.get("common_errors", []),
            show_support_panel=False,  # no nested support
        )

    def _show_item_properties(
        self,
        label: str,
        status: str,
        description: str,
        errors: list[str],
        frame_info: str = "",
        ref_image: str | None = None,
        wiki_enabled: bool = False,
        show_support_panel: bool = True,
    ) -> None:
        self._prop_name.setText(label)
        self._prop_status.setText(
            UI["status_published"] if status == "published" else UI["status_draft"]
        )

        self._prop_description.setEnabled(True)
        self._prop_description.setPlainText(description)

        # Support checklist
        self._prop_support_label.setVisible(show_support_panel)
        self._prop_support_hint.setVisible(show_support_panel)
        self._prop_support_checklist.setVisible(show_support_panel)
        if show_support_panel:
            self._populate_support_checklist(self._current_item_id)

        self._prop_errors.setEnabled(True)
        self._prop_errors.setPlainText("\n".join(errors))

        self._prop_ref_img_label.setText(
            Path(ref_image).name if ref_image else UI["no_reference_image"]
        )
        self._prop_frame_info.setText(
            f"{UI['timestamp_auto']}: {frame_info}"
            if frame_info else UI["timestamp_auto"] + ": —"
        )
        self._btn_wiki.setEnabled(wiki_enabled)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _format_frame_info(stance: dict) -> str:
    ts = stance.get("timestamp_start")
    te = stance.get("timestamp_end")
    if ts is not None and te is not None:
        return f"{ts:.2f}s – {te:.2f}s"
    return "—"


def _stub_message(parent: QWidget, action: str) -> None:
    QMessageBox.information(
        parent, action,
        f"'{action}' wird in einem späteren Entwicklungsschritt implementiert."
    )


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFrameShadow(QFrame.Shadow.Sunken)
    return line


def _bold_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-weight: bold; font-size: 11px;")
    return lbl
