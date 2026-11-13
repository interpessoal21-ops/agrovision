import unittest

from streamlit.testing.v1 import AppTest


class AppStartupTests(unittest.TestCase):
    def test_visitor_can_open_the_full_application(self):
        app = AppTest.from_file("app.py", default_timeout=90).run()
        self.assertFalse(
            app.exception,
            msg="The initial login screen raised an exception: "
            + "; ".join(str(item.message) for item in app.exception),
        )

        visitor_buttons = [
            button for button in app.button
            if "Continue as visitor" in button.label
            or "Continuar como visitante" in button.label
        ]
        self.assertEqual(len(visitor_buttons), 1, "Visitor entry button was not rendered")
        visitor_buttons[0].click().run(timeout=120)

        self.assertFalse(
            app.exception,
            msg="The full visitor application raised an exception: "
            + "; ".join(str(item.message) for item in app.exception),
        )
        self.assertTrue(
            any("GUMA" in str(item.value) for item in app.markdown),
            "The GUMA application content was not rendered",
        )


if __name__ == "__main__":
    unittest.main()
