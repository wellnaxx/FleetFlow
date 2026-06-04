import unittest
from unittest.mock import MagicMock

from src.application.exceptions.application_errors import ValidationError
from src.application.use_cases.pagination import PageQuery, execute_page_query


class ExecutePageQueryShould(unittest.TestCase):
    def test_returns_unpaginated_items(self) -> None:
        list_all = MagicMock(return_value=("a", "b"))
        list_page = MagicMock()
        list_page_with_total = MagicMock()

        result = execute_page_query(
            query=PageQuery(),
            list_all=list_all,
            list_page=list_page,
            list_page_with_total=list_page_with_total,
        )

        self.assertEqual(result.items, ("a", "b"))
        self.assertIsNone(result.total)
        self.assertIsNone(result.limit)
        self.assertEqual(result.offset, 0)
        self.assertEqual(result.count, 2)
        list_all.assert_called_once_with()
        list_page.assert_not_called()
        list_page_with_total.assert_not_called()

    def test_rejects_offset_without_limit(self) -> None:
        list_all = MagicMock()
        list_page = MagicMock()
        list_page_with_total = MagicMock()

        with self.assertRaises(ValidationError) as ctx:
            execute_page_query(
                query=PageQuery(offset=1),
                list_all=list_all,
                list_page=list_page,
                list_page_with_total=list_page_with_total,
            )

        self.assertIn("Offset cannot be used without a limit.", str(ctx.exception))
        list_all.assert_not_called()
        list_page.assert_not_called()
        list_page_with_total.assert_not_called()

    def test_returns_page_without_total(self) -> None:
        list_all = MagicMock()
        list_page = MagicMock(return_value=["a"])
        list_page_with_total = MagicMock()

        result = execute_page_query(
            query=PageQuery(limit=10, offset=20),
            list_all=list_all,
            list_page=list_page,
            list_page_with_total=list_page_with_total,
        )

        self.assertEqual(result.items, ("a",))
        self.assertIsNone(result.total)
        self.assertEqual(result.limit, 10)
        self.assertEqual(result.offset, 20)
        self.assertEqual(result.count, 1)
        list_all.assert_not_called()
        list_page.assert_called_once_with(10, 20)
        list_page_with_total.assert_not_called()

    def test_returns_page_with_total(self) -> None:
        list_all = MagicMock()
        list_page = MagicMock()
        list_page_with_total = MagicMock(return_value=(["a"], 3))

        result = execute_page_query(
            query=PageQuery(limit=10, offset=20, include_total=True),
            list_all=list_all,
            list_page=list_page,
            list_page_with_total=list_page_with_total,
        )

        self.assertEqual(result.items, ("a",))
        self.assertEqual(result.total, 3)
        self.assertEqual(result.limit, 10)
        self.assertEqual(result.offset, 20)
        self.assertEqual(result.count, 1)
        list_all.assert_not_called()
        list_page.assert_not_called()
        list_page_with_total.assert_called_once_with(10, 20)

    def test_rejects_invalid_limit(self) -> None:
        list_all = MagicMock()
        list_page = MagicMock()
        list_page_with_total = MagicMock()

        with self.assertRaises(ValidationError) as ctx:
            execute_page_query(
                query=PageQuery(limit=0),
                list_all=list_all,
                list_page=list_page,
                list_page_with_total=list_page_with_total,
            )

        self.assertIn("Limit must be greater than zero.", str(ctx.exception))
        list_all.assert_not_called()
        list_page.assert_not_called()
        list_page_with_total.assert_not_called()

    def test_rejects_invalid_offset(self) -> None:
        list_all = MagicMock()
        list_page = MagicMock()
        list_page_with_total = MagicMock()

        with self.assertRaises(ValidationError) as ctx:
            execute_page_query(
                query=PageQuery(limit=1, offset=-1),
                list_all=list_all,
                list_page=list_page,
                list_page_with_total=list_page_with_total,
            )

        self.assertIn("Offset must be greater than or equal to zero.", str(ctx.exception))
        list_all.assert_not_called()
        list_page.assert_not_called()
        list_page_with_total.assert_not_called()
