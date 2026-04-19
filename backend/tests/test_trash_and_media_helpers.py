from pathlib import Path
import sys
import tempfile
import unittest


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.common import album_media_predicate, date_group_media_predicate, pick_asset_media_path
from app.models.image_asset import ImageAsset
from app.models.trash_entry import TrashEntry
from app.services.imports.helpers import unique_dir_dest
from app.services import trash_service


class MediaPathHelperTests(unittest.TestCase):
    def test_pick_asset_media_path_uses_date_group_match(self):
        asset = ImageAsset(
            original_path='original.jpg',
            file_hash='hash-1',
            media_path=[
                'media/2024-07/album/file.jpg',
                'media/2024-07/direct.jpg',
            ],
        )

        media_index, media_rel_path = pick_asset_media_path(asset, date_group_media_predicate('2024-07'))

        self.assertEqual(media_index, 1)
        self.assertEqual(media_rel_path, 'media/2024-07/direct.jpg')

    def test_pick_asset_media_path_uses_album_match(self):
        asset = ImageAsset(
            original_path='original.jpg',
            file_hash='hash-2',
            media_path=[
                'media/2024-07/direct.jpg',
                'media/2024-07/vacation/day1/file.jpg',
            ],
        )

        media_index, media_rel_path = pick_asset_media_path(asset, album_media_predicate('2024-07/vacation/day1'))

        self.assertEqual(media_index, 1)
        self.assertEqual(media_rel_path, 'media/2024-07/vacation/day1/file.jpg')


class UniqueDirDestTests(unittest.TestCase):
    def test_unique_dir_dest_appends_incrementing_suffix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            parent = Path(tmpdir)
            (parent / 'album').mkdir()
            (parent / 'album_1').mkdir()

            candidate = unique_dir_dest(parent, 'album')

            self.assertEqual(candidate, parent / 'album_2')


class TrashStorageHelperTests(unittest.TestCase):
    def test_flat_trash_payload_path_stays_directly_under_trash_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_trash_dir = trash_service.TRASH_DIR
            trash_service.TRASH_DIR = Path(tmpdir)
            try:
                candidate = trash_service._flat_trash_payload_path('entry123', 'photo.jpg')

                self.assertEqual(candidate, Path(tmpdir) / 'entry123__photo.jpg')
                self.assertEqual(candidate.parent, Path(tmpdir))
            finally:
                trash_service.TRASH_DIR = original_trash_dir

    def test_migrate_legacy_trash_payload_flattens_old_payload_folder(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            original_trash_dir = trash_service.TRASH_DIR
            trash_service.TRASH_DIR = Path(tmpdir)
            try:
                legacy_payload_root = trash_service._legacy_trash_payload_root('entry123')
                legacy_payload_root.mkdir(parents=True, exist_ok=True)
                legacy_file = legacy_payload_root / 'photo.jpg'
                legacy_file.write_bytes(b'legacy-payload')

                entry = TrashEntry(
                    entry_key='entry123',
                    entity_type='image',
                    display_name='photo.jpg',
                    original_path='media/2025-03/photo.jpg',
                    trash_path=trash_service.to_project_relative(legacy_file),
                    preview_path=trash_service.to_project_relative(legacy_file),
                )

                migrated_path, changed = trash_service._migrate_legacy_trash_payload(entry, legacy_file)

                self.assertTrue(changed)
                self.assertEqual(migrated_path, Path(tmpdir) / 'entry123__photo.jpg')
                self.assertTrue(migrated_path.exists())
                self.assertEqual(entry.trash_path, migrated_path.as_posix())
                self.assertEqual(entry.preview_path, migrated_path.as_posix())
                self.assertFalse((Path(tmpdir) / 'entries').exists())
            finally:
                trash_service.TRASH_DIR = original_trash_dir

    def test_pick_trash_preview_source_for_album_uses_sorted_first_image(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            payload_dir = Path(tmpdir) / 'album'
            payload_dir.mkdir(parents=True, exist_ok=True)
            (payload_dir / 'z-last.webp').write_bytes(b'z')
            (payload_dir / 'a-first.jpg').write_bytes(b'a')
            (payload_dir / 'note.txt').write_text('ignore me', encoding='utf-8')

            entry = TrashEntry(
                entry_key='entry456',
                entity_type='album',
                display_name='album',
                original_path='2025-03/album',
                trash_path='trash/entry456__album',
            )

            preview_source = trash_service._pick_trash_preview_source(entry, payload_dir)

            self.assertEqual(preview_source, payload_dir / 'a-first.jpg')


if __name__ == '__main__':
    unittest.main()