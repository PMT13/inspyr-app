var all_keywords = [];
var tags_list = [];

function addKeyword(){                                                      // add tag by typing
    var added_keywords = document.getElementById("addedKeywords"); 
    var searchBar = document.getElementById("searchBar").value; 
    if(searchBar != ""){
        if(!all_keywords.includes(searchBar)){
            added_keywords.innerHTML += '<span class="pure-u-1 pure-u-md-1-24" id="newTag" onclick="deleteKeyword(this.id)" style="width:fit-content;"></span>';
            document.getElementById("newTag").id = searchBar;           // give unique id to each added tag
            document.getElementById(searchBar).textContent = searchBar; // change the content of each tag to whatever was manaually typed 
            document.getElementById("searchBar").value = "";            
            all_keywords.push(searchBar);
            if(document.getElementById(searchBar + "1") != null){       // when manually searched, if tag exists already then change the color of that tag and add to tags list
                tags_list.push(searchBar);
                document.getElementById(searchBar + "1").style.backgroundColor = "#2d3e50";
            }
        }else{
            document.getElementById("searchBar").value = "";
        }
    }
    getBoards();
}

function deleteKeyword(keyword){                                // delete the tag when it's clicked on and remove it from the tags_list or all_keywords list
    var delete_keyword = document.getElementById(keyword);
    var keyword_name = delete_keyword.textContent;
    delete_keyword.remove();
    if(all_keywords.includes(keyword_name)){
        var index = all_keywords.indexOf(keyword_name);
        if (index > -1) {
            all_keywords.splice(index, 1);
            if(document.getElementById(keyword_name + "1") != null){
                var index = tags_list.indexOf(keyword_name);     // tag clicked on but was already clicked on before
                if (index > -1) {
                    tags_list.splice(index, 1);
                }
                document.getElementById(keyword_name + "1").style.backgroundColor = "white";
            }
        }
    }
    getBoards();
}   

function addTagToSearch(tag){
    var tagName = tag.slice(0, -1);
    if(!tags_list.includes(tagName)){               // tag clicked on
        tags_list.push(tagName);
        document.getElementById(tag).style.backgroundColor = "#2d3e50"; 
    }else{
        var index = tags_list.indexOf(tagName);     // tag clicked on but was already clicked on before
        if (index > -1) {
            tags_list.splice(index, 1);
        }
        var keyword_dup = all_keywords.includes(tagName);
        if(keyword_dup == true){
            deleteKeyword(tagName);
        }
        document.getElementById(tag).style.backgroundColor = "white"; 
    }
    getBoards();
}

function getBoards(){
    document.getElementById('loading').style.display = 'block';
    var checkBox = document.getElementById("includeAll");
    var includeAll = 'false';
    if (checkBox.checked == true){
       includeAll = 'true';
    } else {
        includeAll = 'false';
    }
    var server_data = [{"keywords": all_keywords,
                        "tags": tags_list,
                        "includeAll": includeAll
                    }];	
    $.ajax({	
        type: "POST",	
        url: "/",	
        data: JSON.stringify(server_data),	
        contentType: "application/json",	
        dataType: 'json' ,	
        success: function(result) {	
            var board_container = document.getElementById("board_container");
            board_container.innerHTML = '<div class="lds-dual-ring" id="loading" style="display: none;"></div>';
            for(i = 0; i < result['boards'].length;i++){
                board_container.innerHTML += 
                '<a href="' + "board/" + result['boards'][i] +'">'+
                '<div class="boardPreview">' + 
                '<h3>' + result['board_names'][i] + '</h3>' +
                '<img class="thumbnail_img" src="' + result['thumbnails'][i] + '" alt=""></img>'
                + '</div>' + '</a>'; 
            }
            document.getElementById('loading').style.display = 'none';
        } 	
    });
}

var searchBar = document.getElementById("searchBar");
if(searchBar != null){
    searchBar.addEventListener("keyup", function(event) {
        // Number 13 is the "Enter" key
        if (event.keyCode === 13) {
            // Cancel the default action, if needed
            event.preventDefault();
            document.getElementById("addKeyword").click();
        }
    });
}

$(document).on("keydown", "form", function(event) { 
    return event.key != "Enter";
});
