/* Footer: the officers' email addresses, shown on click only.
   The page holds each address reversed and base64-encoded (data-e), with no
   "@" and no mail link, and so does the public repository (mkdocs.yml): a
   harvester reading either finds no address. The address is decoded only
   when a reader clicks the email icon, which then becomes a mail link. */
document.addEventListener("click", function (event) {
  var button = event.target.closest("button.md-officers__email[data-e]");
  if (!button) return;
  var address = atob(button.dataset.e).split("").reverse().join("").trim();
  var link = document.createElement("a");
  link.href = "mail" + "to:" + address;
  link.textContent = address;
  button.replaceWith(link);
  link.focus();
});
