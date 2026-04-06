import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AgentWorkbenchPage } from "./pages/AgentWorkbenchPage";
import { CustomerChatPage } from "./pages/CustomerChatPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/customer" replace />} />
        <Route path="/customer" element={<CustomerChatPage />} />
        <Route path="/agent" element={<AgentWorkbenchPage />} />
      </Routes>
    </BrowserRouter>
  );
}
