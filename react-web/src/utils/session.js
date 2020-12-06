// return if the session is active
export const isActiveSession = () => {
  return sessionStorage.getItem('active') || false;
}

// return session CSRF
export const getSessionCSRF = () => {
  return sessionStorage.getItem('CSRF') || null;
}
  
// remove the session storage
export const removeSession = () => {
  sessionStorage.removeItem('active');
  sessionStorage.removeItem('CSRF');
}
  
// set the token and user from the session storage
export const setSession = (CSRF) => {
  sessionStorage.setItem('active', true);
  sessionStorage.setItem('CSRF', CSRF);
}