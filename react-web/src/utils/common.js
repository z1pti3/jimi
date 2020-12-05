// return the token from the session storage
export const isActiveSession = () => {
  return sessionStorage.getItem('active') || false;
}
  
// remove the token and user from the session storage
export const removeSession = () => {
  sessionStorage.removeItem('active');
}
  
// set the token and user from the session storage
export const setSession = () => {
  sessionStorage.setItem('active', true);
}