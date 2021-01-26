export const URL = () => {
  var domain = window.location.hostname;
  var port = window.location.port;
  if (domain === "localhost" && port === "3000") {
    return "http://127.0.0.1:5002/api/1.0/";
  }
  return "/api/1.0/";
}

