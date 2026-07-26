package cl.cctvflow.camera.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val CCTVFlowColors = darkColorScheme(
    primary = Color(0xFF5ED6C0),
    onPrimary = Color(0xFF00382F),
    secondary = Color(0xFFFFC857),
    background = Color(0xFF0D1716),
    surface = Color(0xFF152321),
    surfaceVariant = Color(0xFF20312E),
)

@Composable
fun CCTVFlowTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = CCTVFlowColors,
        content = content,
    )
}

