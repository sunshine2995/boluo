$(document).ready(function(){
	$(".arrowa").click(function(){
    	$(".panel").slideDown("slow");
    	$(".arrowa").css("display","none");
    	$(".arrowb").css("display","block");
    });
    $(".arrowb").click(function(){
    	$(".panel").slideUp("slow");
    	$(".arrowa").css("display","block");
    	$(".arrowb").css("display","none");
    });
    //进度条
    var progress = $(".progress-bar-inner");
    progress.each(function (i)
    {
        var data = $(this).attr('data-value');
        $(this).prev().find("span").html(data+"%");
    });
});

$(function(){
    //点击立即参与
    $(".canyu").click(function(){
    	var login = $('#islogin').val();
    	if (login === 'True') {
    		$('#hdqihao').val($(this).attr('sss'));
    	var num = parseInt($(this).attr('num'));
    	$('#boluobi000').html(num);
    	$(".jianghao").hide();
			    	$(".publish").hide();
			    	$(".participate").hide();
			    	$(".togg_two").hide();
			    	$(".overone").hide();
			    	$(".overtwo").hide();
			    	$(".eject").show();
			    	$(".toggls").show();

			    	$(".add").click(function(){
						var t=$(this).parent().find('input[class*=text_box]');
							t.val(parseInt(t.val())+1)
							setTotal();
					});
					$(".min").click(function(){
						var t=$(this).parent().find('input[class*=text_box]');
							t.val(parseInt(t.val())-1)
							if(parseInt(t.val())<1){
								t.val(1);
							}
							setTotal();
					});

			    	$(".resets_tag").click(function(){
			    		/*window.location.reload();*/ //刷新当前页面
			    		$(".eject").hide();
			    	});
			    	$(".sum").click(function(){
						$(this).attr("disabled", true);
			    		var hdqihao = $('#hdqihao').val();
			    		var num = $('.text_box').val();
			    		var phone = $('#phone').val();
			    		var token = $('#token').val();

						$.ajax({
							url: '/v1/activity/mothersday/ajax/'+phone+'/'+ token +'/'+ num+ '/' + hdqihao,
							type: 'GET',
							cache: false,
							success: function (response_data) {
								if (response_data['status'] === '1'){
									$(".publish").hide();
							    	$(".jianghao").hide();
							    	$(".togg_two").hide();
							    	$(".overtwo").hide();
							    	$(".toggls").hide();
							    	$(".eject").show();
							    	$(".overone").show();
							    	$(".know").click(function(){
							    		$(".eject").hide();
							    		window.location.reload();
							    	});
								} else if (response_data['status'] === '2'){
									$(".publish").hide();
							    	$(".jianghao").hide();
							    	$(".togg_two").hide();
							    	$(".overone").hide();
							    	$(".toggls").hide();
							    	$(".eject").show();
							    	$(".overtwo").show();
									$(".overtwo p").html('您的菠萝不够哦');
							    	$(".know").click(function(){
							    		$(".eject").hide();
							    		window.location.reload();
							    	});
								} else if (response_data['status'] === '99'){
									$(".publish").hide();
							    	$(".jianghao").hide();
							    	$(".togg_two").hide();
							    	$(".overone").hide();
							    	$(".toggls").hide();
							    	$(".eject").show();
							    	$(".overtwo").show();
									$(".overtwo p").html('活动还未开始哦!');
							    	$(".know").click(function(){
							    		$(".eject").hide();
							    		window.location.reload();
							    	});
								}else {
									$(".publish").hide();
							    	$(".jianghao").hide();
							    	$(".togg_two").hide();
							    	$(".overone").hide();
							    	$(".toggls").hide();
							    	$(".eject").show();
							    	$(".overtwo").show();
									$(".overtwo p").html('您参与次数超过限额');

							    	$(".know").click(function(){
							    		$(".eject").hide();
							    		window.location.reload();
							    	});
								}


							}
                    });

			    	});


		} else {
			$(".publish").hide();
	    	$(".jianghao").hide();
	    	$(".toggls").hide();
	    	$(".togg_two").hide();
	    	$(".overone").hide();
	    	$(".overtwo").hide();
	    	$(".eject").show();
	    	$(".participate").show();
	    	$(".quxiao").click(function(){
	    		$(".eject").hide();
	    	});
		}


    })

    //获奖公布
    $(".presson").click(function(){
    	$(".jianghao").hide();
    	$(".toggls").hide();
    	$(".togg_two").hide();
    	$(".participate").hide();
    	$(".overone").hide();
    	$(".overtwo").hide();
    	$(".eject").show();
    	$(".publish").show();
    	var my=new IScroll(".award");
    	$(".sign").click(function(){
    		$(".eject").hide();
    	})
    })
	//我的奖号
    $(".presstw").click(function(){
    	$(".publish").hide();
    	$(".toggls").hide();
    	$(".togg_two").hide();
    	$(".participate").hide();
    	$(".overone").hide();
    	$(".overtwo").hide();
    	$(".eject").show();
    	$(".jianghao").show();
    	var my=new IScroll(".ward");
    	$(".sign").click(function(){
    		$(".eject").hide();
    	})
    })
});