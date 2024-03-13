

// $(document).ready(function(){
//     $.ajax({
// 			url: '/get-collections',
// 			type: 'POST',
// 			success: function(collectionList){
//                 collection = JSON.parse(collectionList)
//                 $.each(collection, function(i, p) {
//                         $('#inputCollection').append($('<option></option>').val(p).html(p));
//                 });
// 			},
// 			error: function(error){
// 				console.log(error);
// 			}
// 		});
// });

function openTab(evt, tabName) {
  // Declare all variables
  var i, tabcontent, tablinks;

  // Get all elements with class="tabcontent" and hide them
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }

  // Get all elements with class="tablinks" and remove the class "active"
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }

  // Show the current tab, and add an "active" class to the button that opened the tab
  document.getElementById(tabName).style.display = "block";
  evt.currentTarget.className += " active";
}



$(document).ready(function(){
    
    const msgerForm = get(".msger-inputarea");
    const msgerInput = get(".msger-input");
    const msgerChat = get(".msger-chat");
    
    // const BOT_IMG = "https://www.flaticon.com/free-icon/user_149071";
    // const PERSON_IMG = "https://www.flaticon.com/free-icon/user_149071";
    // const BOT_NAME = "BOT";
    // const PERSON_NAME = "You";
    
    msgerForm.addEventListener("submit", event => {
      event.preventDefault();
    
      const msgText = msgerInput.value;
      if (!msgText) return;
    
      appendMessage("right", msgText);
      
      botResponse(msgText);
      msgerInput.value = "";
    });
    
    function appendMessage(side, text) {
      //   Simple solution for small apps
      const msgHTML = `
        <div class="msg ${side}-msg">
    
          <div class="msg-bubble">
            <div class="msg-info">
            
            </div>
    
            <span class="msg-text">${text}</span>
          </div>
        </div>
      `;
    
      msgerChat.insertAdjacentHTML("beforeend", msgHTML);
      msgerChat.scrollTop += 500;
    }
    
    function botResponse(query) {
        
      const delay = query.split(" ").length * 100;
        if (query == "") {
            return
        }
        
        var collectionText = "main_collection"
        
        var dataToDB = {"query" : query, "collection" : collectionText}
        $.ajax({
            url: '/query',
            data: dataToDB,
            type: 'POST',
            success: function(dataArray){
                metadatas = dataArray[0][0] // array of 10 objects
                documents = dataArray[1][0] // array of 10 strings\
                console.log("meta")
                console.log(metadatas)
                console.log("documents")
                console.log(documents)
                relevantDocuments = documents.join('\n')
                properties = ["name", "address", "halal", "beverage", "soup", "seafood", "healthy", "fast food",  "local", "countries"]

                // Update the table 
                const table = document.createElement("table");
                const title = document.createElement("caption");
                const titleText = document.createTextNode("Query: " + query);
                title.appendChild(titleText);
                table.appendChild(title);
                title.style.fontSize = "15px";
                title.style.fontWeight = "bold";
                title.style.textAlign = "left";
                title.style.color = "#555";
                title.style.paddingBottom = "10px";
                
                const hrow = document.createElement("tr");
                table.appendChild(hrow);
                

                for(let property of properties)
                    {
                        const th = document.createElement("th");
                        const thtext = document.createTextNode(property);
                        th.appendChild(thtext);
                        hrow.appendChild(th);
                    }

                for(let met of metadatas)
                    {
                        const drow = document.createElement("tr");
                        table.appendChild(drow);
                
                        for(let property of properties)
                        {
                            const td = document.createElement("td");
                            const tdtext = document.createTextNode(met[property]);
                            td.appendChild(tdtext);
                            drow.appendChild(td);
                        }
                    }
                var rawTable = document.getElementById('raw_table')
                rawTable.insertBefore(table, rawTable.firstChild);

                var dataToLLM = {"query" : query, "documents" : relevantDocuments}
                $.ajax({
                    url: '/synthesize-response',
                    data: dataToLLM, 
                    type: 'POST',
                    success: function(response){
                        console.log(response)
                        setTimeout(() => {
                            appendMessage("left", response);
                          }, delay);
                    }
                });
                
            },
            error: function(error){
                console.log(error);
            }
        });
        
    }
    
    // Utils
    function get(selector, root = document) {
      return root.querySelector(selector);
    }
    
    function formatDate(date) {
      const h = "0" + date.getHours();
      const m = "0" + date.getMinutes();
    
      return `${h.slice(-2)}:${m.slice(-2)}`;
    }
    
    function random(min, max) {
      return Math.floor(Math.random() * (max - min) + min);
    }
});