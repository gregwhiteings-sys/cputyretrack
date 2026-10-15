"""Called with the actual bundled executable; no network/camera/SMTP required."""
import json,os,sys,traceback
from pathlib import Path

def run(app_module, output):
    try:
        import torch,torchvision,cv2,depthai,lap,optree,numpy as np
        from scipy.linalg import cho_factor
        from ultralytics import YOLO
        from ultralytics.trackers.byte_tracker import BYTETracker
        from PyQt5.QtWidgets import QApplication
        assert not torch.cuda.is_available(), 'Expected CPU-only build'
        assert torch.__version__.startswith('2.5.1')
        assert torchvision.__version__.startswith('0.20.1')
        assert np.__version__=='1.26.4'
        assert depthai.__version__.startswith('2.')
        cho_factor(np.eye(4))
        boxes=torch.tensor([[0.,0.,10.,10.],[1.,1.,9.,9.]])
        assert torchvision.ops.nms(boxes,torch.tensor([.9,.8]),.5).numel()==1
        model=YOLO(str(app_module.resource_path('tyre_detector.pt')))
        assert model.task=='segment'
        model.track(np.zeros((360,640,3),dtype=np.uint8),imgsz=480,device='cpu',
                    persist=True,tracker='bytetrack.yaml',verbose=False)
        qt=QApplication.instance() or QApplication([])
        # Main builds every control but never runs camera/scheduler during this check.
        original_tick=app_module.Main.tick
        app_module.Main.tick=lambda self:None
        try:
            window=app_module.Main();window.clock.stop();window.resize(1366,768)
            window.show();qt.processEvents()
            for index in range(window.controls_tabs.count()):
                window.controls_tabs.setCurrentIndex(index);qt.processEvents()
                scroll=window.controls_tabs.widget(index)
                assert scroll.widget().width()<=scroll.viewport().width(), 'Clipped control tab'
            assert window.best_daily_card.geometry().top()==window.best_hour_card.geometry().top()
            window.close();qt.processEvents()
        finally:app_module.Main.tick=original_tick
        payload={'status':'passed','torch':torch.__version__,'torchvision':torchvision.__version__,
                 'numpy':np.__version__,'depthai':depthai.__version__,
                 'checks':['imports','scipy','torchvision-nms','bundled-segmentation-model',
                           'CPU-inference-and-ByteTrack','Qt-controls-layout']}
        Path(output).write_text(json.dumps(payload,indent=2));return 0
    except Exception:
        Path(output).write_text(json.dumps({'status':'failed','traceback':traceback.format_exc()},indent=2));return 1
