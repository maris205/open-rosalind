import { useEffect, useState } from 'react';
import Landing from './Landing';
import ChatApp from './ChatApp';

function getRoute() {
  const hash = window.location.hash || '';
  if (hash.startsWith('#/app')) return 'app';
  return 'landing';
}

export default function App() {
  const [route, setRoute] = useState(getRoute());

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  // Reset scroll on route change so chat doesn't keep landing scroll position
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [route]);

  return route === 'app' ? <ChatApp /> : <Landing />;
}
