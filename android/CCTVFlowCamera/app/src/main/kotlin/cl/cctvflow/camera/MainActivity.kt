package cl.cctvflow.camera

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.viewmodel.compose.viewModel
import cl.cctvflow.camera.data.CatalogRepository
import cl.cctvflow.camera.data.CounterRepository
import cl.cctvflow.camera.ui.CCTVFlowApp
import cl.cctvflow.camera.ui.CCTVFlowViewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val factory = CCTVFlowViewModel.Factory(
            catalogRepository = CatalogRepository(applicationContext),
            counterRepository = CounterRepository(applicationContext),
        )

        setContent {
            val appViewModel: CCTVFlowViewModel = viewModel(factory = factory)
            CCTVFlowApp(viewModel = appViewModel)
        }
    }
}

