import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Toaster } from "sonner";
import LeadFinder from "@/components/lead/LeadFinder";
import { AuthProvider } from "@/contexts/AuthContext";
import { AuthGate } from "@/components/auth/AuthGate";

function App() {
  return (
    <div className="App">
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route
              path="/*"
              element={
                <AuthGate>
                  <LeadFinder />
                </AuthGate>
              }
            />
          </Routes>
        </BrowserRouter>
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              borderRadius: 0,
              background: "#0A0A0A",
              color: "#FFFFFF",
              border: "1px solid #0A0A0A",
              fontFamily: "'IBM Plex Sans', sans-serif",
              fontSize: "13px",
            },
          }}
        />
      </AuthProvider>
    </div>
  );
}

export default App;
