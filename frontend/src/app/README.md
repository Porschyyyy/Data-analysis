# AstroPipeline refactor v3

แนวทางนี้แยกเฉพาะ function / logic ออกจาก `page.tsx` แต่ยังคง UI และ `useState` หลักไว้ใน `page.tsx` เพื่อให้โครงหน้าเดิมใช้งานเหมือนเดิม

## ไฟล์ที่เพิ่ม

- `types/pipeline.ts` — รวม type ทั้งหมด เช่น `StepKey`, `TabKey`, `ToolKey`, `PreviewMode`
- `lib/constants.ts` — รวมค่าคงที่ เช่น `API_BASE`, `pipelineSteps`, `tabs`, `toolbarButtons`
- `lib/pipelineApi.ts` — ฟังก์ชันเรียก API และเลือก folder
- `lib/pipelinePayloads.ts` — ฟังก์ชันสร้าง request body สำหรับแต่ละ endpoint
- `lib/pipelineUtils.ts` — helper เช่น parse star positions, validate path, build image url
- `lib/pipelineActions.ts` — action หลัก เช่น run pipeline, run calibration, run photometry, plot only
- `lib/viewerActions.ts` — action สำหรับ toolbar/menu/viewer click
- `page.original.tsx` — ไฟล์เดิมสำรอง

## page.tsx ทำอะไรตอนนี้

- เก็บ state ด้วย `useState`
- แสดง JSX/UI เหมือนเดิม
- สร้าง context จาก state แล้วส่งให้ฟังก์ชันที่แยกออกไป
- เรียกใช้ action เช่น `runPipelineAction`, `plotOnlyAction`, `handleViewerClickAction`
