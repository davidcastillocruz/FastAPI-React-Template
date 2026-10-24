import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router';

// Placeholder until the real pages exist
function Placeholder() {
  return <div>App</div>;
}

const router = createBrowserRouter([
  { path: '/', element: <Placeholder /> },
  { path: '*', element: <Placeholder /> },
]);

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
