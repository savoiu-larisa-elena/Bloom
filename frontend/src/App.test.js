import { render, screen } from '@testing-library/react';
import App from './App';

test('renders welcome screen', () => {
  render(<App />);
  expect(screen.getByText(/welcome to bloom/i)).toBeInTheDocument();
});
