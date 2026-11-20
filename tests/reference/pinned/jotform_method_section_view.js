var MethodSectionView = Backbone.View.extend({

    tagName: "section",
    className: "request-wrapper",

    events: {
        "click .call-method" : "callMethod",
        "click .close-response": "closeResponseWindow",
        "click .demo-heading": "toggleRequestWindow",
        "click .navbar-item": "toggleActive",
        "click .toggle-response": "toggleResponseWindow"
    },

    initialize: function(options){
        _.bindAll(this, "render", "callMethod", "closeResponseWindow", "toggleRequestWindow", "toggleActive", "toggleResponseWindow");

        this.options = options;
        this.render(options);
    },

    render: function(options){

        this.$el.attr("id", options.id);
        this.$el.html(_.template($("#method-section-template").html())(options));

        $("#method-sections").append("<br/>");
        $("#method-sections").append(this.el);

        //to bring first tab open
        $("ul#"+options.id+" a:last").trigger("click");

        var requestCatName = options.url.split('/')[1];
        var requestCategory = options.url.split('/')[1] + "-list";
        if (requestCatName && requestCatName === 'folder') {
            requestCatName = requestCatName + ' (deprecated)';
        }
        if($("#" + requestCategory).length <= 0) {
            $("#method-items").append('<li><div class="cat-cont">/'+requestCatName+'</div><ul class="dn category-list" id='+requestCategory+'></ul></li>');
        }

        //add navbar list item
        $("#"+requestCategory).append('<li class="navbar-item"><a href="#'+options.id+'"><span style="color:#ccc; font-size:12px;">'+options.type+' </span>'+options.url+'</li>');

        //render all sample codes
        $(".code-sample", this.el).each(function(idx, el){
            var l = $(el).attr("data-lang");
            $(el).html($("#"+options.id+"-"+l).html());
        });

        //render all sample codes
        // var l = window.stageModel.get("language");
        // templateLoader.loadRemoteTemplate(l, l+"-code-samples.tmpl", function(t){

        //     var c = $(t).filter("#"+options.id+"-"+l).html();

        //     console.log(c);
        //     if(typeof c !== "undefined"){
        //         c = hljs.highlight("curl",c);
        //         // console.log(c);
        //         $(".code-sample", self.el).each(function(idx, el){
        //             $(el).html(_.template(c));
        //         });
        //     }
        //     //hljs.highlightAuto(c);
        // });

        //render response sample
        $(".response-sample", this.el).html($("#"+options.id+"-response-sample").html())
        //render selected language pre div
        $("."+window.stageModel.get("language"), this.el).show();

        //render date fields
        if($(".datefield", this.el).length>0){
            $(".datefield", this.el).datepicker();
        }
        window.stageModel.on("change", function(){
            $(".code-sample:visible", this.el).hide();
            $("."+window.stageModel.get("language"), this.el).show();            
        });

    },

    callMethod: function(e){
        var self = this;
        var url = this.options.url;
        var domain = window.euOnly && window.euOnly === 1 ? '//eu-api.jotform.com/' : '//api.jotform.com';
        var data = {};
        var queryParameters = {};
        //if apiKey textbox is filled, need to control "useMyApiKey" radio button is checked or not
        var useMyApiKeyStatus = $('input[id^="useMyApiKey"]:checked', this.el).length;

        $("input,textarea", this.el).each(function(idx, el){
            var name = $(el).attr("name");
            var val = window._htmlSanitizer.stripTags($(el).val());
            //ignore empty val
            if (val != null && val.length > 0)
            {
                if($(el).attr("data-inputType")==='query'){
                    queryParameters[name] = val;
                } else if($(el).attr("data-inputType")==='post'){
                        data[name] = val;
                } else if($(el).attr("data-inputType")==='url'){
                    var r = $(el).attr("data-replace");
                    url = url.replace(r, val);
                } else if ($(el).attr("data-inputType")==='JSON') {
                    data = $(el).val();
                }
            }     
        });

        $("select", this.el).each(function(idx, el){
            var name = $(el).attr("name");
            var val = $(el).val();
            
            if($(el).attr("data-inputType")==='query'){
                if(val.length>0){
                    queryParameters[name] = val;
                }
            } else if($(el).attr("data-inputType")==='post'){
                data[name] = val;
            } else if($(el).attr("data-inputType")==='url'){
                var r = $(el).attr("data-replace");
                url = url.replace(r, val);
            }            
        }); 

        $(".datefield", this.el).each(function(idx, el){
            var val = $(el).val();
            if(val.length===0){
                return;
            }

            if($(el).attr("data-inputType")==='query'){
                if(val.length>0){
                    queryParameters[name] = encodeURIComponent(val);
                }
            } else if($(el).attr("data-inputType")==='post'){
                data[name] = encodeURIComponent(val);
            } else if($(el).attr("data-inputType")==='url'){
                var r = $(el).attr("data-replace");
                url = url.replace(r, encodeURIComponent(val));
            } 
        });     

        if(_.keys(queryParameters).length>0){
            var qString = $.param(queryParameters);
            url += "?"+qString;
        }

        var printResponseBody = function(el, responseText){
            if(responseText){
                var escapeText = $("<div>").text(responseText).html();
                var responseBody = $('<div class="preCont"><pre><code class="json">' + JSON.stringify(JSON.parse(escapeText), null, 4) + '</code></pre></div>');
                // if form has any widget, do not use jquery
                if(responseText.includes('control_widget')){
                    el[0].innerHTML = window._htmlSanitizer.sanitizeHTML(responseBody[0].innerHTML);
                }else{
                    el.html(responseBody);
                }
                hljs.highlightBlock(responseBody[0]);
            }else{
                el.html(responseText);
            }
        };

        $.ajax({
            type: this.options.type,
            url: domain + url,
            dataType: "json",
            data: data
        }).done(function(data, status, resp){
            $(".response", self.el).slideUp(500, function(){
                $(".response-url", self.el).html("https://api.jotform.com"+url);

                var r = jQuery.parseJSON(resp.responseText);
                if(r.responseCode == 200){
                    $(".response-code", self.el).html(resp.status);
                    $(".response", self.el).addClass("success");
                    $(".response", self.el).removeClass("fail");
                } else {
                    $(".response-code", self.el).html(r.responseCode);
                    $(".response", self.el).addClass("fail");
                    $(".response", self.el).removeClass("success");
                }
                
                printResponseBody($(".response-body", self.el), resp.responseText)
                $(".response", self.el).slideDown(500, function() {
                    $('[data-spy="scroll"]').each(function () {
                        var $spy = $(this).scrollspy('refresh');
                    });
                });
            });

            var hds= resp.getAllResponseHeaders().split("\n");

            $(".response-headers", self.el).html("");
            _.each(hds, function(h){
                $(".response-headers", self.el).append('<div>'+h+'</div>');
            });
        }).fail(function(resp){
            $(".response", self.el).slideUp(500, function(){
                $(".response-url", self.el).html("https://api.jotform.com"+url);
                $(".response-code", self.el).html(resp.status);
                $(".response", self.el).addClass("fail");
                $(".response", self.el).removeClass("success");
                printResponseBody($(".response-body", self.el), resp.responseText)
                $(".response", self.el).slideDown(500, function() {
                    $('[data-spy="scroll"]').each(function () {
                        var $spy = $(this).scrollspy('refresh');
                    });
                });
            });

            var hds= resp.getAllResponseHeaders().split("\n");
            $(".response-headers", self.el).html("");
            _.each(hds, function(h){
                $(".response-headers", self.el).append('<div>'+h+'</div>');
            });
        }).always(function(resp){
        });

        $('[data-spy="scroll"]').each(function () {
            var $spy = $(this).scrollspy('refresh');
        });
    },

    prepareRequestData: function(){

        var data = {};

        $("input", this.el).each(function(idx, el){
            console.log("inputs", el);
            var name = $(el).attr("name");
            var val = $(el).val();

            console.log("inputs", name, val);
            data[name] = val;
        });

        console.log(data);
    },

    closeResponseWindow: function(){
        $(".response", self.el).slideUp(200, function() {
            $('[data-spy="scroll"]').each(function () {
                var $spy = $(this).scrollspy('refresh');
            });
        });
    },

    toggleRequestWindow: function(e){
        $("li.pull-right", this.el).toggle();
        $(".tab-content-wrapper", this.el).toggle();

        $(".toggle-request", this.el).toggleClass("icon-plus");
        $(".toggle-request", this.el).toggleClass("icon-minus");
        $(".request-info", this.el).toggle();
        // if($(".tab-content-wrapper", this.el).is("visible")){
        //     $(".toggle-request").removeClass("icon-plus");
        // }
    },

    toggleActive: function(){
        $(e.target).addClass("active");
    },

    toggleResponseWindow: function(e){
        $(".response-sample", this.el).slideToggle(400, function() {
            $('[data-spy="scroll"]').each(function () {
                var $spy = $(this).scrollspy('refresh');
            });
        });
        $("i", e.target).toggleClass("icon-minus");
        //$(".response-sample", this.el).animate({height:'toggle'}, 500);
    }

    
});